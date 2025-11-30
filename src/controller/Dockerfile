FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Init venv
RUN uv venv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv pip install --system -e .

# Install OpenTelemetry core packages
RUN uv pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-discover and install all required instrumentations
# This automatically finds and installs packages needed for FastAPI, logging, etc.
RUN opentelemetry-bootstrap -a install

# Copy the application source code
COPY ./src /app/src

# Production command
CMD ["uv", "run", "opentelemetry-instrument", "python", "-m", "src.controller.main"]
