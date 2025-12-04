# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash gbvapp

# Copy requirements files
COPY backend/requirements.txt /app/backend/
COPY frontend/requirements.txt /app/frontend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir -r frontend/requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . /app/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R gbvapp:gbvapp /app

# Switch to non-root user
USER gbvapp

# Expose ports
EXPOSE 5002 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5002/api/health || exit 1