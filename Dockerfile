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
    libpq-dev \
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

# Copy essential application files
COPY --chown=app:app *.py ./
COPY --chown=app:app app/ ./app/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app docker-entrypoint.sh ./

# Copy optional directories if they exist in the repository
# Note: If these directories are missing during deployment,
# remove these lines or use .dockerignore to exclude them
COPY --chown=app:app tools/ ./tools/
COPY --chown=app:app docs/ ./docs/

# Fix line endings and make entrypoint script executable
RUN sed -i 's/\r$//' docker-entrypoint.sh && \
    chmod +x docker-entrypoint.sh && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application with database initialization
CMD ["./docker-entrypoint.sh"]
