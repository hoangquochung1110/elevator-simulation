import asyncio
import json
from typing import Dict, Optional

import structlog

from ..config import (ELEVATOR_COMMANDS, ELEVATOR_REQUESTS_STREAM,
                      ELEVATOR_STATUS, NUM_ELEVATORS)
from ..libs.cache import cache
from ..libs.messaging.event_stream import event_stream
from ..libs.messaging.pubsub import pubsub
from ..models.elevator import Elevator, ElevatorStatus
from ..models.request import Direction, ExternalRequest, InternalRequest

SCHEDULER_GROUP = "scheduler-group"

logger = structlog.get_logger(__name__)


class Scheduler:
    """
    Elevator request scheduler.
    """

    def __init__(
        self,
        id: str,
    ):
        self.id = id
        self.consumer_id = f"scheduler-{id}"
        self.elevator_states: Dict[int, Elevator] = {}
        self._running: bool = False
        self.logger = logger

    async def start(self) -> None:
        """Start the scheduler service."""
        self._running = True

        # Create consumer group
        try:
            await event_stream._backend.create_consumer_group(
                ELEVATOR_REQUESTS_STREAM, SCHEDULER_GROUP
            )
        except Exception as e:
            self.logger.warning(
                "Consumer group creation error, might already exist",
                stream=ELEVATOR_REQUESTS_STREAM,
                group=SCHEDULER_GROUP,
                error=str(e),
            )

        # Load initial elevator states
        await self._load_elevator_states()

        # Main loop to process messages from event stream
        while self._running:
            try:
                messages = await event_stream.read_group(
                    stream=ELEVATOR_REQUESTS_STREAM,
                    group=SCHEDULER_GROUP,
                    consumer=self.consumer_id,
                    count=10,
                    block=1000,  # Block for 1 second
                )

                if not messages:
                    continue

                for stream_name, entries in messages:
                    for message_id, data in entries:
                        await self._handle_message(message_id, data)
                        await event_stream.acknowledge(
                            stream_name, SCHEDULER_GROUP, message_id
                        )

            except asyncio.CancelledError:
                self.logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                self.logger.error("Error in scheduler loop", error=str(e), exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    async def stop(self) -> None:
        """Stop the scheduler and clean up resources."""
        self._running = False

        try:
            from ..libs.messaging.pubsub import close as close_pubsub
            await close_pubsub()
            self.logger.info("Closed pubsub client")
        except Exception as e:
            self.logger.error("Error closing pubsub client", exc_info=True)
        self.logger.info("Scheduler stopped")

    async def _handle_message(self, message_id: str, data: dict) -> None:
        """Handle an incoming message from the event stream."""
        try:
            request_type = data.get("request_type")
            self.logger.info(
                "received_request",
                request_type=request_type,
                data=data,
                message_id=message_id,
            )

            if request_type == "external":
                request = ExternalRequest.from_dict(data)
                await self._handle_external_request(request)
            elif request_type == "internal":
                request = InternalRequest.from_dict(data)
                await self._handle_internal_request(request)
        except Exception as e:
            self.logger.error(
                "message_handling_error",
                message_id=message_id,
                error=str(e),
                exc_info=True,
            )

    async def _handle_external_request(self, request: ExternalRequest):
        elevator_id = await self._select_best_elevator_for_external(request)
        if elevator_id:
            command = {
                "correlation_id": request.id,
                "command": "go_to_floor",
                "floor": request.floor,
                "request_id": request.id,
            }
            await pubsub.publish(
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

    async def _handle_internal_request(self, request: InternalRequest):
        command = {
            "correlation_id": request.id,
            "command": "add_destination",
            "floor": request.destination_floor,
            "request_id": request.id,
        }
        await pubsub.publish(
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
                self.logger.warning(f"Elevator {elevator_id} state not found in cache.")
                # Initialize with a default state if not found
                state = {
                    "id": elevator_id,
                    "current_floor": 1,
                    "status": "idle",
                    "door_status": "closed",
                    "destinations": [],
                }
                await cache.set(key, state)
            self.elevator_states[elevator_id] = Elevator.from_dict(state)

    async def _select_best_elevator_for_external(
        self, request: ExternalRequest
    ) -> Optional[int]:
        best_elevator_id = None
        best_score = float("inf")
        self.logger.info(
            "serving_request",
            request_id=request.id,
            floor=request.floor,
            direction=request.direction.name,
        )
        for elevator_id, state in self.elevator_states.items():
            score = self._calculate_score(state, request.floor, request.direction)
            self.logger.info(
                "elevator_score",
                request_id=request.id,
                elevator_id=elevator_id,
                score=score,
            )
            if score < best_score:
                best_score = score
                best_elevator_id = elevator_id
        return best_elevator_id

    def _calculate_score(
        self, elevator_state: Elevator, request_floor: int, request_direction: Direction
    ) -> float:
        current_floor = elevator_state.current_floor
        status = elevator_state.status
        distance = abs(current_floor - request_floor)
        score = float(distance)

        if status == ElevatorStatus.IDLE:
            score -= 1
        elif status in (ElevatorStatus.MOVING_UP, ElevatorStatus.MOVING_DOWN):
            is_on_way = (status == ElevatorStatus.MOVING_UP and request_direction == Direction.UP and request_floor >= current_floor) or \
                        (status == ElevatorStatus.MOVING_DOWN and request_direction == Direction.DOWN and request_floor <= current_floor)
            score *= 0.8 if is_on_way else 5.0

        return score
