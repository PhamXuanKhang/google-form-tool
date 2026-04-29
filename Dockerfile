# Google Form Automation Tool
# Multi-stage build for smaller image size

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Install Chrome and ChromeDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set Chrome paths for Linux
ENV CHROME_BINARY_PATH=/usr/bin/chromium
ENV CHROME_DRIVER_PATH=/usr/bin/chromedriver

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app/ ./app/
COPY config.py .
COPY wsgi.py .

# Create data directory for TinyDB
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/db.json

# Flask configuration
ENV FLASK_DEBUG=0
ENV SECRET_KEY=change-me-in-production

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Run with production server
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=5000", "wsgi:app"]
