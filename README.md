## Redis-PubSub-101: Elevator Simulation Dashboard

This project simulates a multi-elevator system with a web-based dashboard.

- FastAPI for HTTP endpoints handling internal & external elevator requests
- HTMX for live polling/UI updates without heavy JavaScript
- **Redis Pub/Sub** as the backbone message broker:
  - Requests published on `elevator:requests`
  - Scheduler assigns via `elevator:commands:{id}` channels
  - Controllers broadcast state on `elevator:status:{id}`

## Core Components
- UI Dashboard
- FastAPI endpoints
- Redis Pub/Sub
- Scheduler
- Controllers

## Data Flow Patterns

### 1. Floor Call Request Flow

When a passenger presses a call button on a floor:

1. API publishes request to `elevator:requests`
2. Scheduler receives message via subscription
3. Scheduler queries all elevator states from Redis hashes
4. Scheduler applies optimization algorithm to determine best elevator
5. Scheduler publishes command to `elevator:commands:{chosen_id}`
6. Selected Elevator Controller receives command via subscription
7. Controller adds floor to its destination sorted set
8. Controller begins movement and publishes status updates
9. Controller updates its state hash for persistence (optional)

### 2. Elevator Movement Sequence

As an elevator moves between floors:

1. Controller updates internal state (position, direction)
2. Controller publishes status update to `elevator:status:{id}`
3. Controller updates its hash at `elevator:{id}:state` 
4. WebSocket server receives status update and forwards to UI
5. UI reflects elevator movement in real-time

### 3. Multi-Elevator Coordination

When multiple elevators are operating simultaneously:

1. Each Controller operates independently, subscribing only to its command channel
2. The Scheduler maintains system-wide awareness by reading all elevator states
3. Status updates flow through separate channels, preventing message congestion
4. The Scheduler optimizes assignments based on current positions and movements of all elevators

## Redis Data Structures Used

### 1. Pub/Sub Channels

Used for real-time communication between components:
- `elevator:requests` - All passenger requests enter the system
- `elevator:commands:{id}` - Individual command channel for each elevator
- `elevator:status:{id}` - Status updates from each elevator
- `elevator:system` - System-wide notifications and events (not in use for now)

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