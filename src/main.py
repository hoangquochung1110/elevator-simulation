# src/main.py
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .channels import ELEVATOR_REQUESTS, ELEVATOR_STATUS, ELEVATOR_SYSTEM

from .channels import (
    ELEVATOR_COMMANDS,
    ELEVATOR_REQUESTS,
    ELEVATOR_STATUS,
    ELEVATOR_SYSTEM,
    ELEVATOR_REQUESTS_STREAM,
)
from .config import NUM_ELEVATORS, NUM_FLOORS, configure_logging, redis_client


# --- Startup and shutdown events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    # initialize elevator states in Redis
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        initial_state = {
            "id": i,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": [],
        }
        await redis_client.set(key, json.dumps(initial_state))
    yield


app = FastAPI(title="Redis Pub/Sub API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")


class PublishRequest(BaseModel):
    channel: str = Field(..., description="One of the predefined channels")
    message: Any = Field(..., description="Payload to publish; will be JSON‑encoded")

    @field_validator("channel")
    def check_channel(cls, v: str) -> str:
        fixed = {ELEVATOR_REQUESTS, ELEVATOR_SYSTEM}
        if (
            v in fixed
            or v.startswith("elevator:commands:")
            or v.startswith("elevator:status:")
        ):
            return v
        raise ValueError(f"invalid channel: {v!r}")


class ExternalRequestModel(BaseModel):
    """Model for external elevator requests (floor call buttons)."""

    floor: int = Field(
        ...,
        ge=1,
        le=NUM_FLOORS,
        description="Floor number where the button was pressed",
    )
    direction: str = Field(..., description="Direction (up or down)")

    model_config = ConfigDict(
        json_schema_extra={"example": {"floor": 3, "direction": "up"}}
    )


class InternalRequestModel(BaseModel):
    """Model for internal elevator requests (destination buttons)."""

    elevator_id: int = Field(
        ..., ge=1, le=NUM_ELEVATORS, description="ID of the elevator"
    )
    destination_floor: int = Field(..., ge=1, le=NUM_FLOORS, description="Target floor")

    model_config = ConfigDict(
        json_schema_extra={"example": {"elevator_id": 1, "destination_floor": 5}}
    )


async def fetch_elevator_statuses() -> list[dict]:
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
        eid = int(key.split(":")[-1])
        statuses.append((eid, data))
    statuses.sort(key=lambda x: x[0])
    return [data for _, data in statuses]


@app.post("/api/requests/internal", status_code=202)
async def create_internal_request(req: InternalRequestModel):
    # serialize Pydantic model to JSON string
    request_data = req.model_dump()
    request_data.update(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "id": str(uuid.uuid4()),
            "request_type": "internal",
            "status": "pending",
        }
    )
    payload = json.dumps(request_data)
    await redis_client.publish(ELEVATOR_REQUESTS, payload)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS}


@app.post("/api/requests/external", status_code=202)
async def create_external_request(req: ExternalRequestModel):
    # serialize Pydantic model to JSON string
    request_data = req.model_dump()
    request_data.update(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "id": str(uuid.uuid4()),
            "request_type": "external",
            "status": "pending",
        }
    )
    payload = json.dumps(request_data)

    await redis_client.publish(ELEVATOR_REQUESTS, payload)
    # Streams should accept Python dict
    await redis_client.xadd(ELEVATOR_REQUESTS_STREAM, request_data)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS}


@app.get("/api/elevators", status_code=200)
async def get_elevators():
    return {"elevators": await fetch_elevator_statuses()}


@app.get("/api/requests", status_code=200)
async def get_stream_requests():
    """Retrieve all entries from the elevator requests stream"""
    entries = await redis_client.xrange(ELEVATOR_REQUESTS_STREAM, "-", "+")
    requests = []
    for msg_id, fields in entries:
        # include message ID with each entry
        entry = {"id": msg_id}
        entry.update(fields)
        requests.append(entry)
    return {"requests": requests}


@app.delete("/api/requests", status_code=200)
async def trim_stream(
    min_id: Optional[str] = Query(None, description="Exclusive start ID; entries with ID < min_id will be removed"),
    maxlen: Optional[int] = Query(None, description="Maximum number of entries to keep"),
    approximate: bool = Query(True, description="Whether to use approximate trimming"),
):
    """
    Trim the elevator requests stream using XTRIM.
    Only one of min_id or maxlen must be provided.
    """
    # Enforce exclusive parameters
    if (min_id is None and maxlen is None) or (min_id is not None and maxlen is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one of min_id or maxlen")
    # Trim by count
    if maxlen is not None:
        trimmed_count = await redis_client.xtrim(
            ELEVATOR_REQUESTS_STREAM,
            maxlen=maxlen,
            approximate=approximate,
        )
    else:
        # Trim by ID
        trimmed_count = await redis_client.xtrim(
            ELEVATOR_REQUESTS_STREAM,
            minid=min_id,
            approximate=approximate,
        )
    return {"trimmed": trimmed_count}


@app.get("/elevator-table", response_class=HTMLResponse)
async def elevator_table(request: Request):
    elevators = await fetch_elevator_statuses()
    return templates.TemplateResponse(
        "elevator_table.html", {"request": request, "elevators": elevators}
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    result = await get_elevators()
    elevators = result["elevators"]
    return templates.TemplateResponse(
        "index.html", {"request": request, "elevators": elevators}
    )
