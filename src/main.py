# src/main.py
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .channels import (ELEVATOR_COMMANDS, ELEVATOR_REQUESTS, ELEVATOR_STATUS,
                       ELEVATOR_SYSTEM)
from .config import NUM_ELEVATORS, NUM_FLOORS, redis_client


# --- Startup and shutdown events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize elevator states in Redis
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        initial_state = {
            "id": i,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        }
        await redis_client.set(key, json.dumps(initial_state))
    yield

app = FastAPI(title="Redis Pub/Sub API", lifespan=lifespan)


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
    request_data = req.model_dump()
    request_data.update({
        "timestamp": datetime.utcnow().isoformat(),
        "id": str(uuid.uuid4()),
        "request_type": "external",
        "status": "pending",
    })
    payload = json.dumps(request_data)

    await redis_client.publish(ELEVATOR_REQUESTS, payload)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS}


@app.get("/elevators", status_code=200)
async def get_elevators():
    # dynamically fetch all elevator status keys
    statuses = []
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        raw = await redis_client.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        # extract elevator id from key
        eid = int(key.split(":")[-1])
        statuses.append((eid, data))
    # sort by elevator id
    statuses.sort(key=lambda x: x[0])
    elevators = [data for _, data in statuses]
    return {"elevators": elevators}
