FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy pyproject.toml and install dependencies from it
COPY pyproject.toml .
RUN uv pip install --system -e .

# Copy the src directory to maintain the correct import structure
COPY ./src /app/src

EXPOSE 8000

# Update the command to use the correct module path
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
