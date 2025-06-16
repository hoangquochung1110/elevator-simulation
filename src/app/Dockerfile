FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv pip install --system -e .

# Only copy __init__.py as placeholder, rest will be mounted
COPY ./src/__init__.py /app/src/

EXPOSE 8000

# Run with reload flag for development
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]
