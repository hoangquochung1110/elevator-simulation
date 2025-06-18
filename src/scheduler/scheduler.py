import asyncio
import json
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import structlog
from redis.exceptions import ConnectionError, RedisError

from ..config import (ELEVATOR_COMMANDS, ELEVATOR_REQUESTS_STREAM,
                      ELEVATOR_STATUS, NUM_ELEVATORS, get_redis_client)
from ..models.elevator import Elevator, ElevatorStatus
from ..models.request import Direction, ExternalRequest, InternalRequest
from ..libs.messaging.event_stream import (EventStreamClient, StreamProvider,
                                           create_stream_client)
from ..libs.messaging.pubsub import (PubSubClient, PubSubProvider,
                                     create_pubsub_client)


SCHEDULER_GROUP = "scheduler-group"

logger = structlog.get_logger(__name__)

MAX_RETRIES = 3

async def _exponential_backoff(attempt: int, max_delay: int = 32) -> None:
    """Calculate exponential backoff delay with jitter."""
    delay = min(max_delay, (2 ** attempt) + (random.random() * 0.1))
    await asyncio.sleep(delay)

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

    def __init__(self, id):
        self.id = id
        self.consumer_id = f"scheduler-{id}"
        self.redis_client = None
        self.event_stream = None
        self.pubsub = None
        self.elevator_states: Dict[int, Elevator] = {}
        self._running: bool = False
        self.logger = logger
        # Logger handlers and level are configured centrally in application entry-point

    async def start(self) -> None:
        self._running = True
        self.redis_client = await get_redis_client()
        if not self.event_stream:
            self.event_stream = await create_stream_client(
                provider=StreamProvider.REDIS
            )
        # Ensure consumer group exists
        await self.event_stream.create_consumer_group(
            stream=ELEVATOR_REQUESTS_STREAM,
            group=SCHEDULER_GROUP,
            mkstream=True,
        )


        # Load initial elevator states
        await self._load_elevator_states()

        # Claim and process any pending entries for this consumer
        pending_stream_entries = self.event_stream.resume_processing
        if pending_stream_entries:
            for stream_name, messages in pending_stream_entries:
                for message in messages:
                    await self._handle_message(message)
                    self.event_stream.acknowledge(
                        stream=ELEVATOR_REQUESTS_STREAM,
                        group=SCHEDULER_GROUP,
                        message_ids=[message.id]
                    )

        # Claim and process any pending entries for this consumer
        # async with redis_xreadgroup_with_ack(
        #     self.redis_client,
        #     group_name=SCHEDULER_GROUP,
        #     consumer_name=self.consumer_id,
        #     streams={ELEVATOR_REQUESTS_STREAM: "0"},
        #     auto_ack=True,
        #     max_retries=MAX_RETRIES,
        # ) as pending_stream_entries:
        #     # Process pending entries
        #     if pending_stream_entries:
        #         for stream_name, messages in pending_stream_entries:
        #             for message in messages:
        #                 await self._handle_message(message)

        # subscribe to the elevator requests channel
        while self._running:
            try:
                # Block up to 1 second for new, unseen entries
                # async with redis_xreadgroup_with_ack(
                #     self.redis_client,
                #     group_name=SCHEDULER_GROUP,
                #     consumer_name=self.consumer_id,
                #     streams={ELEVATOR_REQUESTS_STREAM: ">"},
                #     auto_ack=True,
                #     max_retries=MAX_RETRIES,
                # ) as stream_entries:
                #     if not stream_entries:
                #         self.logger.debug("No new stream entries")
                #         continue
                #     for stream, messages in stream_entries:
                #         for message in messages:
                #             await self._handle_message(message)
                stream_entries = self.event_stream.read_group(
                    stream=ELEVATOR_REQUESTS_STREAM,
                    group=SCHEDULER_GROUP,
                    consumer=self.consumer_id
                )
                if not stream_entries:
                    self.logger.debug("No new stream entries")
                    continue
                for message in stream_entries:
                    await self._handle_message(message)
                    self.event_stream.acknowledge(
                    stream=ELEVATOR_REQUESTS_STREAM,
                    group=SCHEDULER_GROUP,
                    message_ids=[message.id]
                )

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
            await self.redis_client.publish(
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
        await self.redis_client.publish(
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
            state = await self.redis_client.get(key)
            if state:
                # Convert to proper types
                self.elevator_states[elevator_id] = Elevator.from_dict(
                    json.loads(state)
                )
            else:
                raise ValueError(f"Elevator {elevator_id} not found")

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
