FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/db/migrations

# Copy application code
COPY app app/
COPY tests tests/
COPY main.py .
COPY pytest.ini .
COPY .env.local .

# Create entrypoint script
RUN echo '#!/bin/bash\n\
uvicorn main:app --host 0.0.0.0 --port 8000 --reload' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
