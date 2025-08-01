# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create app user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Create directories for logs, data, and database
RUN mkdir -p /app/logs /app/static/img /app/instance \
    && chown -R app:app /app/logs /app/static /app/instance

# Copy application files
COPY port_tracer_web.py .
COPY database.py .
COPY migrate.py .
COPY cpu_safety_monitor.py .
COPY switch_protection_monitor.py .
COPY nt_auth_integration.py .
COPY switches.json .
COPY static/ ./static/
COPY instance/ ./instance/

# Set ownership of all files to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "port_tracer_web.py"]
