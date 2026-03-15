FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and install dependencies first (cache layer)
COPY pyproject.toml ./
COPY app/__init__.py ./app/
RUN pip install --no-cache-dir .

# Copy application code
COPY . .
RUN pip install --no-cache-dir --no-deps .

# Create data directories
RUN mkdir -p data/vault data/chroma data/audit data/temp logs/traces

# Create non-root user
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser
RUN chown -R appuser:appuser /app/data /app/logs
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/v1/system/liveness || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
