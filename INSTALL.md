## Installation

### Prerequisites

- Docker and Docker Compose

### Running Services

Start all services with:

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

### Configuration

The system can be configured using environment variables:

- `REDIS_HOST`: Redis host (defaults to "redis)
- `REDIS_PORT`: Redis port (defaults to 6379)
- `REDIS_PASSWORD`: Redis password (optional)
- `REDIS_DB`: Redis database number (defaults to 0)
