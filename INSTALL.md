## Installation

### Prerequisites

- Docker and Docker Compose

### Running Services

All services have been containerized for easy deployment:

```sh
docker compose up -d
```

This will start:

- Redis server
- Web application (FastAPI)
- Scheduler service
- Controller service

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
