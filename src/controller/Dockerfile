FROM python:3.12-slim

WORKDIR /app

# Install uv (keeping consistent with your webapp Dockerfile)
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv pip install --system -e .

# Only copying __init__.py as a placeholder for development
COPY ./src/__init__.py /app/src/

# Add watchdog for auto-reloading in development
RUN pip install watchdog[watchmedo]

# Use watchmedo to auto-reload on file changes
CMD ["watchmedo", "auto-restart", "--directory=/app/src", "--pattern=*.py", "--recursive", "--", "python", "-m", "src.controller.main"]
