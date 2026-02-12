# Multi-stage build for optimized image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Install playwright browsers
RUN playwright install chromium && \
    playwright install-deps chromium

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies and playwright deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && pip install playwright \
    && playwright install-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser

# Set work directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

# Copy application code
COPY --chown=appuser:appuser . .

# Create logs directory and set permissions
RUN mkdir -p logs analytics/reports && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run bot
CMD ["python", "bot.py"]
