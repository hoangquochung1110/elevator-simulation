FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv sync --frozen --no-dev

# Auto-discover and install all required instrumentations
# This automatically finds and installs packages needed for FastAPI, logging, etc.
RUN uv run opentelemetry-bootstrap -a requirements | uv pip install --requirement -

# Add the venv to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY ./src /app/src

EXPOSE 8000

# Use instrumentation wrapper with uv run
CMD ["uv", "run", "opentelemetry-instrument", "uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
