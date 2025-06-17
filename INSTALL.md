## Installation

### Prerequisites

- Docker and Docker Compose

### Running Services

The system can run in two modes: single Redis instance (development) or Redis Cluster (production).

#### Development Mode (Single Redis Instance)

```sh
docker compose --profile single up -d
```

This will start:

- Single Redis server
- Web application (FastAPI)
- Scheduler service
- Controller service

#### Production Mode (Redis Cluster)

```sh
# Set environment variables for cluster mode
export REDIS_CLUSTER_MODE=true
export REDIS_SERVICE=redis-cluster
export REDIS_HOST=redis-cluster

# Start the services with cluster profile
docker compose --profile cluster up -d
```

This will start:

- Redis Cluster (3 masters + 3 replicas)
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

- `REDIS_CLUSTER_MODE`: Set to "true" for cluster mode, "false" for single instance
- `REDIS_HOST`: Redis host (defaults to "redis" for single instance, "redis-cluster" for cluster mode)
- `REDIS_PORT`: Redis port (defaults to 6379)
- `REDIS_PASSWORD`: Redis password (optional)

### Scaling Considerations

- In single instance mode, all Redis operations go to one server
- In cluster mode, data is automatically sharded across multiple nodes
- The application code handles both modes transparently through the Redis adapter
