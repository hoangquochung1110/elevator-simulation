FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv pip install --system -e .

# Auto-discover and install instrumentations
RUN uv run opentelemetry-bootstrap -a requirements | uv pip install --requirement -

# Copy application code
COPY ./src /app/src

EXPOSE 8000

# Use instrumentation wrapper with uv run
CMD ["opentelemetry-instrument", "uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["uv", "run", "opentelemetry-instrument", "uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
