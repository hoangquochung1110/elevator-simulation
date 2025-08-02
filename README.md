## Redis-PubSub-101: Elevator Simulation Dashboard

This project simulates a multi-elevator system with a web-based dashboard.

- FastAPI for HTTP endpoints handling internal & external elevator requests
- HTMX for live polling/UI updates without heavy JavaScript
- **Redis Messaging** as the backbone communication system:
  - **Redis Streams** for reliable request processing:
    - Requests published to `elevator:requests:stream`
    - Consumer groups ensure each request is processed exactly once
  - **Redis Pub/Sub** for real-time status updates:
    - Scheduler assigns via `elevator:commands:{id}` channels
    - Controllers broadcast state on `elevator:status:{id}`

## Core Components

- UI Dashboard
- FastAPI endpoints
- Redis Streams & Pub/Sub
- Scheduler
- Controllers

## Data Flow Patterns

### 1. Floor Call Request Flow

When a passenger presses a call button on a floor:

1. API adds request to `elevator:requests:stream` using Redis Streams
2. Scheduler consumes message from the stream via consumer group
3. Scheduler queries all elevator states from Redis hashes
4. Scheduler applies optimization algorithm to determine best elevator
5. Scheduler publishes command to `elevator:commands:{chosen_id}` via Pub/Sub
6. Selected Elevator Controller receives command via subscription
7. Controller adds floor to its destination sorted set
8. Controller begins movement and publishes status updates
9. Controller updates its state hash for persistence (optional)
10. Scheduler acknowledges the processed message in the stream

### 2. Elevator Movement Sequence

As an elevator moves between floors:

1. Controller updates internal state (position, direction)
2. Controller publishes status update to `elevator:status:{id}` via Pub/Sub
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

### 1. Redis Streams

Used for reliable request processing:

- `elevator:requests:stream` - All passenger requests enter the system through this stream
  - Consumer groups ensure each request is processed exactly once
  - Provides persistence and recovery capabilities

### 2. Pub/Sub Channels

Used for real-time communication between components:

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
4. No look‑ahead or idle repositioning
   - Idle cars stay parked where they last dropped off.
   - In practice, elevators often return to a “home” floor or stage themselves near anticipated traffic zones.
5. No capacity or load handling
   - There’s no notion of elevator “full,” so calls can be sent to a car even if it’s overloaded.
   - Real controllers track load and may skip further stops when at capacity.
6. No priority handling

## Logging with Loki and Promtail

This project uses Grafana Loki for log aggregation and Promtail for log collection, providing a powerful and efficient logging solution.

### Prerequisites
- Docker and Docker Compose installed
- Ports 3100 (Loki) and 9080 (Promtail) available

### 1. Starting the Logging Services

To start the logging infrastructure along with the main application:

```bash
docker-compose up -d loki promtail
```

To include the entire application stack:

```bash
docker-compose up -d
```

### 2. Accessing Logs

#### Option A: Grafana (Recommended)
1. Add Grafana to your `docker-compose.yml`:
   ```yaml
   grafana:
     image: grafana/grafana:latest
     ports:
       - "3000:3000"
     volumes:
       - grafana-storage:/var/lib/grafana
     networks:
       - logging
     depends_on:
       - loki
   ```
2. Access Grafana at `http://localhost:3000`
3. Add Loki as a data source:
   - URL: `http://loki:3100`
   - Click "Save & test"
4. Explore logs using the "Explore" tab

#### Option B: Loki API
Query logs directly using the Loki API:
```bash
# Get recent logs
curl -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={job="app_logs"}' \
  --data-urlencode 'limit=50' | jq .
```

### 3. Log Collection Details

- **Application Logs**: Stored in `./logs/` directory
  - Supports both plain text (`*.log`) and JSON (`*.json`) formats
  - Automatically collected and parsed by Promtail

- **Container Logs**: Collected from all running containers
  - Includes logs from all services in the stack

### 4. Log Querying in Grafana

Use LogQL to query logs in Grafana:

```sql
# Show all application logs
{job="app_logs"}

# Filter by log level
{job="app_logs"} |~ "level=error"

# Search for specific terms
{job=~"app_logs"} |~ "error"

# Show container logs
{job="containerlogs"}
```

### 5. Log Rotation and Retention

- Logs are stored in the `loki_data` volume
- Default retention: 30 days (configurable in `loki/loki-config.yml`)
- To clean up old logs:
  ```bash
  docker-compose exec loki logcli --addr=http://loki:3100 --org-id=0 delete --older-than=720h --query='{job=~"app_logs|containerlogs"}'
  ```

### 6. Exploring Logs in Grafana

Grafana provides a powerful interface for exploring and visualizing your logs. Here's how to get started:

#### Accessing the Explore View
1. Click on the "Explore" icon (compass) in the left sidebar
2. Select "Loki" as your data source from the dropdown at the top

#### Useful LogQL Queries

**View all application logs**
```
{job="app_logs"}
```

**Filter by log level**
```
{job="app_logs"} | json | level = "ERROR"
```

**Search for specific terms**
```
{job="app_logs"} |~ "elevator"
```

**View logs from the last 15 minutes**
```
{job="app_logs"} | json | __error__ = ""
```

**Count logs by level**
```
sum(count_over_time({job="app_logs"} | json | __error__ = "" [5m])) by (level)
```

#### Tips for Effective Log Exploration
- Use the time range selector in the top right to adjust the time window
- Click on log labels to filter by specific values
- Hover over log lines to see additional details
- Use the "Split" button to compare different queries side by side
- Save frequently used queries as dashboard variables for quick access

#### Creating Dashboards
1. Click on "Dashboards" in the left sidebar
2. Click "New Dashboard"
3. Add a new panel and select the Loki data source
4. Use LogQL queries to create visualizations of your log data

#### Example Dashboard Panels
1. **Error Rate**
   ```
   sum(count_over_time({job="app_logs"} | json | level = "ERROR" [5m]))
   ```
   Visualization: Time series with a 5-minute step

2. **Log Volume by Level**
   ```
   sum(count_over_time({job="app_logs"} | json | __error__ = "" [5m])) by (level)
   ```
   Visualization: Stacked bars with legend toggles

3. **Top Error Messages**
   ```
   sum(count_over_time({job="app_logs"} | json | level = "ERROR" [1h])) by (message)
   ```
   Visualization: Table sorted by count

## CI/CD Setup

The CI/CD pipeline, defined in `.github/workflows/cicd.yml`, automates the building, testing, and deployment of this application to AWS ECS.

### Terraform State Bucket

The pipeline uses Terraform to manage infrastructure as code. Terraform needs a remote backend to store its state file, which is crucial for collaboration and running automation. We use an AWS S3 bucket for this purpose.

Before the pipeline can run successfully, you must configure the following secret in your GitHub repository's settings (`Settings > Secrets and variables > Actions`):

-   `TF_STATE_BUCKET`: This secret should contain the name of the S3 bucket that you have created to store the Terraform state file (e.g., `my-cool-project-tfstate`).

### AWS Credentials

For GitHub Actions to authenticate with your AWS account and deploy resources, you must also configure the following secrets:

-   `AWS_ACCESS_KEY_ID`: Your AWS access key ID.
-   `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key.

These credentials should belong to an IAM user or role with appropriate permissions to push images to ECR, manage ECS services, and interact with S3 for Terraform state.
