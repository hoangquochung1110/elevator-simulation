FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv sync --frozen --no-dev

# Add the venv to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Auto-discover and install all required instrumentations
# This automatically finds and installs packages needed for FastAPI, logging, etc.
RUN uv run opentelemetry-bootstrap -a requirements | uv pip install --requirement -

# Copy application code
COPY ./src /app/src

# Production command
CMD ["uv", "run", "opentelemetry-instrument", "python", "-m", "src.scheduler.main"]