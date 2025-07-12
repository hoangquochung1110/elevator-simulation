# src/main.py
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

from ..config import (
    ELEVATOR_REQUESTS_STREAM,
    ELEVATOR_STATUS,
    NUM_ELEVATORS,
    NUM_FLOORS,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    configure_logging,
)
from ..libs.cache import cache
from ..libs.cache import close as close_cache
from ..libs.cache import init_cache
from ..libs.messaging.event_stream import close as close_event_stream
from ..libs.messaging.event_stream import event_stream, init_event_stream

load_dotenv()  # take environment variables


# --- Startup and shutdown events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging
    configure_logging()

    # Initialize Cache Service
    init_cache(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
    )

    # Initialize Event Stream Service
    init_event_stream(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
    )

    # Initialize elevator statuses in cache
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        if not await cache.exists(key):
            initial_state = {
                "id": i,
                "current_floor": 1,
                "status": "idle",
                "door_status": "closed",
                "destinations": [],
            }
            await cache.set(key, initial_state)

    try:
        yield
    finally:
        # Cleanup
        await close_cache()
        await close_event_stream()


app = FastAPI(title="Elevator Simulation", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/app/static"), name="static")
templates = Jinja2Templates(directory="src/app/templates")


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
    """Fetch all elevator statuses from cache."""
    statuses = []
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        data = await cache.get(key)
        if data:
            statuses.append((i, data))
    # Sort by elevator ID
    statuses.sort(key=lambda x: x[0])
    return [data for _, data in statuses]


@app.post("/api/requests/internal", status_code=202)
async def create_internal_request(req: InternalRequestModel):
    request_data = req.model_dump()
    request_data.update(
        {
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4()),
            "request_type": "internal",
            "status": "pending",
        }
    )
    await event_stream.publish(ELEVATOR_REQUESTS_STREAM, request_data)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS_STREAM}


@app.post("/api/requests/external", status_code=202)
async def create_external_request(req: ExternalRequestModel):
    request_data = req.model_dump()
    request_data.update(
        {
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4()),
            "request_type": "external",
            "status": "pending",
        }
    )
    await event_stream.publish(ELEVATOR_REQUESTS_STREAM, request_data)
    return {"status": "queued", "channel": ELEVATOR_REQUESTS_STREAM}


@app.get("/api/elevators", status_code=200)
async def get_elevators():
    """Get current status of all elevators."""
    return {"elevators": await fetch_elevator_statuses()}


@app.get("/api/requests", status_code=200)
async def get_stream_requests():
    """Retrieve all entries from the elevator requests stream"""
    entries = await event_stream.range(ELEVATOR_REQUESTS_STREAM, "-", "+")
    requests = []
    for msg_id, fields in entries:
        entry = {"id": msg_id, **fields}
        requests.append(entry)
    return {"requests": requests}


@app.delete("/api/requests", status_code=200)
async def trim_stream(
    min_id: Optional[str] = Query(
        None, description="Exclusive start ID; entries with ID < min_id will be removed"
    ),
    maxlen: Optional[int] = Query(None, description="Maximum number of entries to keep"),
    approximate: bool = Query(True, description="Whether to use approximate trimming"),
):
    """
    Trim the elevator requests stream using XTRIM.
    Only one of min_id or maxlen must be provided.
    """
    trimmed_count = await event_stream.trim(
        ELEVATOR_REQUESTS_STREAM,
        min_id=min_id,
        maxlen=maxlen,
        approximate=approximate,
    )
    return {"trimmed": trimmed_count}


@app.get("/elevator-table")
async def elevator_table(request: Request):
    """Render the elevator table view."""
    elevators = await fetch_elevator_statuses()
    return templates.TemplateResponse(
        "elevator_table.html",
        {"request": request, "elevators": elevators, "num_floors": NUM_FLOORS},
    )


@app.get("/")
async def index(request: Request):
    """Render the main index page."""
    elevators = await fetch_elevator_statuses()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "elevators": elevators},
    )