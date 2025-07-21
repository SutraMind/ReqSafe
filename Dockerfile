# Multi-stage Docker build for Memory Management Module
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "memory_management.api.memory_api"]


# Development stage
FROM base as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio black flake8 mypy

# Install debugging tools
RUN pip install --no-cache-dir ipdb pdbpp

USER appuser

# Override command for development
CMD ["python", "-m", "memory_management.api.memory_api", "--reload"]


# Production stage
FROM base as production

# Copy only necessary files for production
COPY --from=base /app /app

# Set production environment
ENV ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    LOG_ENABLE_FILE=true \
    LOG_FILE=/app/logs/memory_management.log

# Use production command
CMD ["python", "-m", "memory_management.api.memory_api"]