# Backend production Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY backend ./backend
COPY main.py ./

# Install uv and dependencies
RUN pip install uv
RUN uv sync --frozen

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
