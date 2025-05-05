This document is to guide you through the installation and setup of the Redis Pub/Sub 101 project.

## Installation

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
  