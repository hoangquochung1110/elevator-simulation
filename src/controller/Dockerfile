FROM python:3.12-slim

WORKDIR /app

# Install uv (keeping consistent with your webapp Dockerfile)
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv sync --frozen --group dev

# Add the venv to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source code
COPY ./src /app/src

# Production command
CMD ["python", "-m", "src.controller.main"]
