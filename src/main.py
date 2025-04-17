# src/main.py
import json
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .config import redis_client, NUM_ELEVATORS, NUM_FLOORS
from .channels import (
    ELEVATOR_REQUESTS,
    ELEVATOR_COMMANDS,
    ELEVATOR_STATUS,
    ELEVATOR_SYSTEM,
)

app = FastAPI(title="Redis Pub/Sub API")

class PublishRequest(BaseModel):
    channel: str = Field(..., description="One of the predefined channels")
    message: Any = Field(..., description="Payload to publish; will be JSON‑encoded")

    @field_validator("channel")
    def check_channel(cls, v: str) -> str:
        fixed = {ELEVATOR_REQUESTS, ELEVATOR_SYSTEM}
        if v in fixed or v.startswith("elevator:commands:") or v.startswith("elevator:status:"):
            return v
        raise ValueError(f"invalid channel: {v!r}")


class ExternalRequestModel(BaseModel):
    """Model for external elevator requests (floor call buttons)."""
    floor: int = Field(..., ge=1, le=NUM_FLOORS, description="Floor number where the button was pressed")
    direction: str = Field(..., description="Direction (up or down)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "floor": 3,
                "direction": "up"
            }
        }
    )


class InternalRequestModel(BaseModel):
    """Model for internal elevator requests (destination buttons)."""
    elevator_id: int = Field(..., ge=1, le=NUM_ELEVATORS, description="ID of the elevator")
    destination_floor: int = Field(..., ge=1, le=NUM_FLOORS, description="Target floor")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "elevator_id": 1,
                "destination_floor": 5
            }
        }
    )


@app.post("/requests/internal", status_code=202)
async def create_internal_request(req: InternalRequestModel):
    # serialize Pydantic model to JSON string
    payload = req.model_dump_json()
    await redis_client.publish(ELEVATOR_REQUESTS, payload)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS}


@app.post("/requests/external", status_code=202)
async def create_external_request(req: ExternalRequestModel):
    # serialize Pydantic model to JSON string
    payload = req.model_dump_json()
    await redis_client.publish(ELEVATOR_REQUESTS, payload)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS}


@app.get("/elevators", status_code=200)
async def get_elevators():
    elevators = []

    for i in range(1, NUM_ELEVATORS + 1):
        channel = ELEVATOR_STATUS.format(i)
        status = await redis_client.get(channel)
        if status:
            elevators.append(json.loads(status))
        else:
            elevators.append({"id": i, "status": "offline"})
    return {"elevators": elevators}
