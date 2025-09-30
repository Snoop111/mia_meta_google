# Marketing Analytics MCP Server Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies including supervisor
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements-data-apis.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-data-apis.txt

# Copy application code
COPY . .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs && \
    chmod 755 /app/data /app/logs

# Remove supervisor - single service only

# Create non-root user for security  
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080

# Start FastAPI with FastMCP integration
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]