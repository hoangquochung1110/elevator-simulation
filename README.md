## Redis-PubSub-101: Elevator Simulation Dashboard

This project simulates a multi-elevator system with a web-based dashboard.

- FastAPI for HTTP endpoints handling internal & external elevator requests
- HTMX for live polling/UI updates without heavy JavaScript
- **Redis Pub/Sub** as the backbone message broker:
  - Requests published on `elevator:requests`
  - Scheduler assigns via `elevator:commands:{id}` channels
  - Controllers broadcast state on `elevator:status:{id}`

## Getting Started

### Prerequisites

- Redis server (>= 5.x)

### Running Services

1. Start Redis:
   ```sh
   docker compose up -d
   ```
2. Start the FastAPI web app:
   ```sh
   uvicorn src.main:app --reload
   ```
3. Start the scheduler and controllers:
   ```sh
   python -m src.services.run_services
   ```
4. (Optional) Start the log subscriber:
   ```sh
   python src/subscriber.py
   ```

### Accessing the Dashboard

Open your browser at http://localhost:8000/

### Using the REST API

- **External request** (floor call):
  ```sh
  curl -X POST http://localhost:8000/api/requests/external \
       -H "Content-Type: application/json" \
       -d '{"floor": 3, "direction": "up"}'
  ```
- **Internal request** (destination button):
  ```sh
  curl -X POST http://localhost:8000/api/requests/internal \
       -H "Content-Type: application/json" \
       -d '{"elevator_id": 1, "destination_floor": 5}'
  ```

## Limitations
1. Simple FIFO stops
    - In \_process_movement, you pop destinations one‐by‐one in arrival order—even if they’re behind you or in the “wrong” direction mid‑trip.
    - Real elevators group all same‑direction stops before reversing to minimize wasted travel.
2. No direction‑based batching
    - The scheduler’s “nearest” algorithm ignores whether an elevator is already moving up or down.
    - Real controllers only pick up calls that match an elevator’s current direction until it runs out of same‑direction stops.
3. No dynamic reordering
    - New internal/external requests simply append or insert at one end.
    - Production controllers re‑evaluate and re‑order the stop list on every new request to optimize grouping.
3. No look‑ahead or idle repositioning
    - Idle cars stay parked where they last dropped off.
    - In practice, elevators often return to a “home” floor or stage themselves near anticipated traffic zones.
4. No capacity or load handling
    - There’s no notion of elevator “full,” so calls can be sent to a car even if it’s overloaded.
    - Real controllers track load and may skip further stops when at capacity.
5. No priority handling