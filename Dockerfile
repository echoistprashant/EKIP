FROM python:3.12-slim

WORKDIR /app

# Install basic system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appgroup . .

# Create writable upload staging directory before dropping privileges
RUN mkdir -p /app/data/uploads && chown -R appuser:appgroup /app/data

# Switch to non-root user
USER appuser

# Expose port
ENV PORT=8000
EXPOSE 8000

# Run uvicorn bound to 0.0.0.0 and dynamic cloud $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
