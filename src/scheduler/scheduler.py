import asyncio
import json
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import structlog
from redis.exceptions import ConnectionError

from ..config import (ELEVATOR_COMMANDS, ELEVATOR_REQUESTS_STREAM,
                      ELEVATOR_STATUS, NUM_ELEVATORS)
from ..libs.cache import cache
from ..libs.messaging.event_stream import EventStreamClient
from ..libs.messaging.pubsub import PubSubClient
from ..models.elevator import Elevator, ElevatorStatus
from ..models.request import Direction, ExternalRequest, InternalRequest

SCHEDULER_GROUP = "scheduler-group"

logger = structlog.get_logger(__name__)

MAX_RETRIES = 3

async def _exponential_backoff(attempt: int, max_delay: int = 32) -> None:
    """Calculate exponential backoff delay with jitter."""
    delay = min(max_delay, (2 ** attempt) + (random.random() * 0.1))
    await asyncio.sleep(delay)

@asynccontextmanager
async def readgroup_with_ack(
    event_stream,
    stream,
    group,
    consumer,
    last_id,
    auto_ack,
    max_retries=3
):
    """Asynchronous context manager for reading and acknowledging messages from a stream consumer group.

    This function handles reading messages from a distributed stream with built-in retry logic
    for connection errors and optional automatic message acknowledgment.

    Args:
        event_stream: The stream client instance used for reading and acknowledging messages.
        stream (str): Name of the stream to read from.
        group (str): Name of the consumer group.
        consumer (str): Name of the consumer within the group.
        last_id (str): The ID from which to start reading messages. Use '>' to get new messages.
        auto_ack (bool): If True, automatically acknowledge messages after they are successfully processed.
        max_retries (int, optional): Maximum number of retry attempts for connection errors. Defaults to 3.

    Yields:
        list: A list of tuples containing stream entries in the format (stream_name, [(entry_id, fields_dict), ...]).

    Raises:
        ConnectionError: If maximum retry attempts are exceeded for connection errors.
        Exception: Any other unexpected exceptions that occur during stream processing.

    Note:
        - The function implements exponential backoff between retry attempts.
        - When auto_ack is True, messages are only acknowledged if no exceptions occur during processing.
        - Connection errors are automatically retried up to max_retries times.
        - The function assumes the underlying stream supports consumer groups and message acknowledgment.
    """
    entries_to_ack = []
    attempt = 0

    while True:
        try:
            stream_data = await event_stream.read_group(
                stream=stream,
                group=group,
                consumer=consumer,
                last_id=last_id,
            )
            # Collect entries for acknowledgment
            for stream_name, stream_entries in stream_data:
                for entry_id, fields in stream_entries:
                    entries_to_ack.append((stream_name, entry_id))
            # Yield in original format
            yield stream_data

            # Auto-acknowledge all entries if enabled and no exception occurred
            if auto_ack and entries_to_ack:
                try:
                    # Group entries by stream for efficient acking
                    streams_to_ack = {}
                    for stream_name, entry_id in entries_to_ack:
                        if stream_name not in streams_to_ack:
                            streams_to_ack[stream_name] = []
                        streams_to_ack[stream_name].append(entry_id)

                    # Acknowledge entries for each stream
                    for stream_name, entry_ids in streams_to_ack.items():
                        await event_stream.acknowledge(
                            stream,
                            group,
                            *entry_ids
                        )
                except Exception as e:
                    logger.error(
                        "Failed to acknowledge messages",
                        error=str(e),
                        stream_name=stream,
                        group_name=group,
                        entries=entry_ids,
                        exc_info=True
                    )
                    raise

            # If we get here, everything worked, so break the retry loop
            break

        except ConnectionError as e:
            # Handle transient connection errors with retry logic
            attempt += 1
            if attempt >= max_retries:
                logger.error(
                    "Max retries exceeded for Redis operation",
                    error=str(e),
                    attempt=attempt,
                    exc_info=True
                )
                raise

            logger.warning(
                "Redis connection error, retrying",
                error=str(e),
                attempt=attempt,
                max_retries=max_retries
            )
            await _exponential_backoff(attempt)

        except Exception as e:
            # Log any other exceptions before re-raising
            logger.error(
                "Unexpected error in redis_xreadgroup_with_ack",
                error=str(e),
                error_type=type(e).__name__,
                group_name=group,
                consumer_name=consumer,
                stream=stream,
                exc_info=True
            )
            raise

@asynccontextmanager
async def redis_xreadgroup_with_ack(
    redis_client,
    group_name: str,
    consumer_name: str,
    streams: Dict[str, str],
    count: Optional[int] = None,
    block: Optional[int] = None,
    auto_ack: bool = True,
    max_retries: int = 3
) -> AsyncGenerator[List[Tuple[str, List[Tuple[str, Dict]]]], None]:
    """
    Context manager that wraps xreadgroup with automatic acknowledgment and retry logic.

    Args:
        redis_client: Redis client instance
        group_name: Consumer group name
        consumer_name: Consumer name within the group
        streams: Dictionary of stream names and IDs
        count: Maximum number of entries to read
        block: Blocking timeout in milliseconds
        auto_ack: Whether to automatically acknowledge messages
        max_retries: Maximum number of retry attempts for transient errors
    """
    logger = structlog.get_logger(__name__)
    entries_to_ack = []
    attempt = 0

    while True:
        try:
            # Read from streams
            stream_data = await redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams=streams,
                count=count,
                block=block
            )

            # Collect entries for acknowledgment
            for stream_name, stream_entries in stream_data:
                for entry_id, fields in stream_entries:
                    entries_to_ack.append((stream_name, entry_id))

            # Yield in original format
            yield stream_data

            # Auto-acknowledge all entries if enabled and no exception occurred
            if auto_ack and entries_to_ack:
                try:
                    # Group entries by stream for efficient acking
                    streams_to_ack = {}
                    for stream_name, entry_id in entries_to_ack:
                        if stream_name not in streams_to_ack:
                            streams_to_ack[stream_name] = []
                        streams_to_ack[stream_name].append(entry_id)

                    # Acknowledge entries for each stream
                    for stream_name, entry_ids in streams_to_ack.items():
                        await redis_client.xack(stream_name, group_name, *entry_ids)
                except Exception as e:
                    logger.error(
                        "Failed to acknowledge messages",
                        error=str(e),
                        stream_name=stream_name,
                        group_name=group_name,
                        entries=entry_ids,
                        exc_info=True
                    )
                    raise

            # If we get here, everything worked, so break the retry loop
            break

        except ConnectionError as e:
            # Handle transient connection errors with retry logic
            attempt += 1
            if attempt >= max_retries:
                logger.error(
                    "Max retries exceeded for Redis operation",
                    error=str(e),
                    attempt=attempt,
                    exc_info=True
                )
                raise

            logger.warning(
                "Redis connection error, retrying",
                error=str(e),
                attempt=attempt,
                max_retries=max_retries
            )
            await _exponential_backoff(attempt)

        except Exception as e:
            # Log any other exceptions before re-raising
            logger.error(
                "Unexpected error in redis_xreadgroup_with_ack",
                error=str(e),
                error_type=type(e).__name__,
                group_name=group_name,
                consumer_name=consumer_name,
                streams=streams,
                exc_info=True
            )
            raise


class Scheduler:
    """
    Elevator request scheduler.

    This service:
    1. Listens for new requests on elevator:requests
    """

    def __init__(
        self,
        id: str,
        pubsub: PubSubClient,
        event_stream: EventStreamClient,
        config: Optional[Dict] = None
    ):
        """Initialize the Scheduler with its dependencies.

        Args:
            id: Unique identifier for this scheduler instance
            pubsub: PubSub client for message passing
            event_stream: Event stream client for stream operations
            config: Optional configuration dictionary
        """
        self.id = id
        self.consumer_id = f"scheduler-{id}"
        self.pubsub = pubsub
        self.event_stream = event_stream
        self.config = config or {}
        self.elevator_states: Dict[int, Elevator] = {}
        self._running: bool = False
        self.logger = logger

    async def create_consumer_group(
        self,
        stream,
        group,
    ):
        # Ensure consumer group exists
        created = await self.event_stream.create_consumer_group(
            stream,
            group,
        )
        return created

    async def start(self) -> None:
        """Start the scheduler service.

        This initializes the consumer group and starts processing requests.
        """
        self._running = True

        # Initialize consumer group
        await self.create_consumer_group(
            ELEVATOR_REQUESTS_STREAM,
            SCHEDULER_GROUP
        )

        # Load initial elevator states
        await self._load_elevator_states()

        # Claim and process any pending entries for this consumer
        async with readgroup_with_ack(
                    event_stream=self.event_stream,
                    stream=ELEVATOR_REQUESTS_STREAM,
                    group=SCHEDULER_GROUP,
                    consumer=self.consumer_id,
                    last_id="0",
                    auto_ack= True,
                    max_retries=3,
        ) as pending_stream_entries:
            if pending_stream_entries:
                for stream_name, messages in pending_stream_entries:
                    for message in messages:
                        await self._handle_message(message)

        # subscribe to the elevator requests channel
        while self._running:
            try:
                async with readgroup_with_ack(
                    event_stream=self.event_stream,
                    stream=ELEVATOR_REQUESTS_STREAM,
                    group=SCHEDULER_GROUP,
                    consumer=self.consumer_id,
                    last_id=">",
                    auto_ack= True,
                    max_retries=3,
                ) as stream_entries:
                    if not stream_entries:
                        self.logger.debug("No new stream entries")
                        continue
                    for stream, messages in stream_entries:
                        for message in messages:
                            await self._handle_message(message)
            except Exception:
                self.logger.error("Error in scheduler loop", exc_info=True)
                await asyncio.sleep(1)

    async def _handle_message(self, message) -> None:
        """
        Handle an incoming message from Redis.

        Args:
            message: The Redis pub/sub message
        """
        msg_id, data = message
        try:
            # Message processing logic
            request_type = data.get("request_type")
            self.logger.info(
                "received_request: %s",
                request_type=request_type,
                data=data,
            )
            if request_type == "external":
                request = ExternalRequest.from_dict(data)
                await self._handle_external_request(request)
            elif request_type == "internal":
                request = InternalRequest.from_dict(data)
                await self._handle_internal_request(request)
        except Exception:
            self.logger.error(
                "message_handling_error",
                message_id=msg_id,
                exc_info=True,
            )

    async def _handle_external_request(self, request):
        # Decide which elevator should handle this request
        elevator_id = await self._select_best_elevator_for_external(request)
        if elevator_id:
            command = {
                "correlation_id": request.id,
                "command": "go_to_floor",
                "floor": request.floor,
                "request_id": request.id,
            }
            # publish command to a channel
            await self.pubsub.publish(
                ELEVATOR_COMMANDS.format(elevator_id), json.dumps(command)
            )
            self.logger.info(
                "assigned_external_request",
                floor=request.floor,
                elevator_id=elevator_id,
                request_id=request.id,
            )
        else:
            self.logger.warning(
                "no_suitable_elevator",
                floor=request.floor,
                request_id=request.id,
                direction=request.direction.name,
            )

    async def _handle_internal_request(self, request):
        # prepare add_destination command
        command = {
            "correlation_id": request.id,
            "command": "add_destination",
            "floor": request.destination_floor,
            "request_id": request.id,
        }
        # publish command to a channel
        await self.pubsub.publish(
            ELEVATOR_COMMANDS.format(request.elevator_id), json.dumps(command)
        )
        self.logger.info(
            "assigned_internal_request",
            elevator_id=request.elevator_id,
            floor=request.destination_floor,
            request_id=request.id,
        )

    async def _load_elevator_states(self) -> None:
        for elevator_id in range(1, NUM_ELEVATORS + 1):
            key = ELEVATOR_STATUS.format(elevator_id)
            state = await cache.get(key)
            if state is None:
                raise ValueError(f"Elevator {elevator_id} not found")
            # Convert to proper types
            self.elevator_states[elevator_id] = Elevator.from_dict(state)

    async def _select_best_elevator_for_external(
        self, request: ExternalRequest
    ) -> Optional[int]:
        """
        Select the best elevator to handle an external request.

        This implements a simple "nearest available elevator" algorithm.

        Args:
            request: The external request to assign

        Returns:
            ID of the selected elevator, or None if no suitable elevator found
        """
        best_elevator_id = None
        best_score = float("inf")  # Lower is better
        self.logger.info(
            "serving_request",
            request_id=request.id,
            floor=request.floor,
            direction=request.direction.name,
        )
        # Calculate a score for each elevator (distance-based)
        for elevator_id, state in self.elevator_states.items():
            score = await self._calculate_score(state, request.floor, request.direction)
            self.logger.info(
                "elevator_score",
                request_id=request.id,
                elevator_id=elevator_id,
                score=score,
            )
            # Keep track of best elevator
            if score < best_score:
                best_score = score
                best_elevator_id = elevator_id

        return best_elevator_id

    async def _calculate_score(
        self, elevator_state: Elevator, request_floor: int, request_direction: Direction
    ) -> float:
        """
        Calculate a score indicating suitability of an elevator for a request.

        This implements a simple scoring system based on distance and status.

        Args:
            elevator_state: The state of the elevator to score
            request_floor: The floor of the request
            request_direction: The direction of the request

        Returns:
            A score indicating the suitability of the elevator for the request. Lower is better.
        """
        # Lower score is better.
        current_floor = elevator_state.current_floor
        status = elevator_state.status

        distance = abs(current_floor - request_floor)
        score = float(distance)  # Base score is distance

        if status == ElevatorStatus.IDLE:
            # Idle elevators are good candidates
            score -= 1  # Bonus for being idle
        elif status in (ElevatorStatus.MOVING_UP, ElevatorStatus.MOVING_DOWN):
            # Check if elevator is moving toward the requested floor in the same direction
            is_on_way = (
                status == ElevatorStatus.MOVING_UP
                and request_direction == Direction.UP
                and request_floor >= current_floor
            ) or (
                status == ElevatorStatus.MOVING_DOWN
                and request_direction == Direction.DOWN
                and request_floor <= current_floor
            )

            # Apply bonus or penalty based on whether elevator is on the way
            score *= 0.8 if is_on_way else 5.0

        return score
