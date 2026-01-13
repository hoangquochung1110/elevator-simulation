FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only dependency files first
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies in a separate layer
RUN uv sync --frozen

# Add the venv to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source code
COPY ./src /app/src

EXPOSE 8000

# Production command
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
