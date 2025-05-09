FROM python:3.12-slim

WORKDIR /app

# Install uv (keeping consistent with your webapp Dockerfile)
RUN pip install --no-cache-dir uv

# Copy pyproject.toml for dependencies
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system -e .

# Copy only the necessary code
# This selective copying reduces image size and improves build caching
COPY ./src/__init__.py /app/src/
COPY ./src/config /app/src/config/
COPY ./src/models /app/src/models/
COPY ./src/scheduler /app/src/scheduler/

# Set environment to development for better console logging
ENV ENV=development

# Command to run the scheduler service
CMD ["python", "-m", "src.scheduler.main"]