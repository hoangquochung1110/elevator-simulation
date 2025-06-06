import asyncio
import json
from typing import Dict, Optional

import structlog
from redis.exceptions import RedisError

from ..config import (ELEVATOR_COMMANDS, ELEVATOR_REQUESTS_STREAM,
                      ELEVATOR_STATUS, NUM_ELEVATORS, redis_client)
from ..models.elevator import Elevator, ElevatorStatus
from ..models.request import Direction, ExternalRequest, InternalRequest

SCHEDULER_GROUP = "scheduler-group"

logger = structlog.get_logger(__name__)

class Scheduler:
    """
    Elevator request scheduler.

    This service:
    1. Listens for new requests on elevator:requests
    """

    def __init__(self, id):
        self.id = id
        self.consumer_id = f"scheduler-{id}"
        self.redis_client = redis_client
        self.elevator_states: Dict[int, Elevator] = {}
        self._running: bool = False
        self.logger = logger
        # Logger handlers and level are configured centrally in application entry-point

    async def start(self) -> None:
        self._running = True
        # Ensure consumer group exists
        try:
            await self.redis_client.xgroup_create(ELEVATOR_REQUESTS_STREAM, SCHEDULER_GROUP, mkstream=True)
        except RedisError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # Load initial elevator states
        await self._load_elevator_states()

        # Claim and process any pending entries for this consumer
        pending_stream_entries = await self.redis_client.xreadgroup(
            groupname=SCHEDULER_GROUP,
            consumername=self.consumer_id,
            streams={ELEVATOR_REQUESTS_STREAM: "0"},
        )
        if pending_stream_entries:
            for _, messages in pending_stream_entries:
                for message in messages:
                    await self._handle_message(message)

        # subscribe to the elevator requests channel
        while self._running:
            try:
                # Block up to 1 second for new, unseen entries
                stream_entries = await self.redis_client.xreadgroup(
                    groupname=SCHEDULER_GROUP,
                    consumername=self.consumer_id,
                    streams={ELEVATOR_REQUESTS_STREAM: ">"},
                )
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
            self.logger.info("Received %s request: %s", request_type, data)
            if request_type == "external":
                request = ExternalRequest.from_dict(data)
                await self._handle_external_request(request)
            elif request_type == "internal":
                request = InternalRequest.from_dict(data)
                await self._handle_internal_request(request)

            # TODO: "publisher" should implement request-reply pattern
            # or side table for tracking processed messages
            await self.redis_client.xack(ELEVATOR_REQUESTS_STREAM, SCHEDULER_GROUP, msg_id)
        except Exception:
            self.logger.error("Error processing message %s", msg_id, exc_info=True)

    async def _handle_external_request(self, request):
        # Decide which elevator should handle this request
        elevator_id = await self._select_best_elevator_for_external(request)
        if elevator_id:
            self.logger.info(
                f"Handling external request from floor {request.floor} to elevator {elevator_id}"
            )
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
        self.logger.info(
            f"Handling external request from floor {request.destination_floor} to elevator {request.elevator_id}"
        )
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
