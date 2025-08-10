FROM python:3.12-slim

WORKDIR /app

# Install uv (keeping consistent with your webapp Dockerfile)
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv pip install --system -e .

# Copy the application source code
COPY ./src /app/src

# Production command
CMD ["python", "-m", "src.controller.main"]
