# Multi-stage build for frontend and backend
FROM node:18-alpine AS frontend-builder

# Set working directory for frontend
WORKDIR /app/web

# Copy frontend package files
COPY web/package*.json ./

# Install all dependencies (including dev dependencies for build)
RUN npm ci

# Copy frontend source code
COPY web/ ./

# Ensure public directory exists
RUN mkdir -p public

# Build frontend for production
RUN npm run build

# Python stage for backend
FROM python:3.11-slim AS backend-builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY api/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY api/ ./

# Production stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend source code
COPY api/ ./

# Ensure migration files are present
RUN ls -la /app/migrations/ || echo "No migrations directory found"
RUN ls -la /app/alembic.ini || echo "No alembic.ini found"

# Copy built frontend from builder
COPY --from=frontend-builder /app/web/out ./web/out
COPY --from=frontend-builder /app/web/.next ./web/.next
COPY --from=frontend-builder /app/web/public ./web/public

# No nginx needed - Flask will serve everything

# Create startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Debug information' >> /app/start.sh && \
    echo 'echo "Starting NDA Redlining Application..."' >> /app/start.sh && \
    echo 'echo "Current directory: $(pwd)"' >> /app/start.sh && \
    echo 'echo "Python version: $(python --version)"' >> /app/start.sh && \
    echo 'echo "Checking frontend files..."' >> /app/start.sh && \
    echo 'ls -la /app/web/' >> /app/start.sh && \
    echo 'ls -la /app/web/out/' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Set environment variables' >> /app/start.sh && \
    echo 'export FLASK_ENV=production' >> /app/start.sh && \
    echo 'export PORT=${PORT:-5001}' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Keep uploads and redlines on the Railway volume so deploys do not wipe them' >> /app/start.sh && \
    echo 'DATA_DIR="${DATA_DIR:-$RAILWAY_VOLUME_MOUNT_PATH}"' >> /app/start.sh && \
    echo 'if [ -n "$DATA_DIR" ]; then' >> /app/start.sh && \
    echo '  for d in uploads outputs; do' >> /app/start.sh && \
    echo '    mkdir -p "$DATA_DIR/$d"' >> /app/start.sh && \
    echo '    if [ ! -L "/app/$d" ]; then rm -rf "/app/$d"; ln -s "$DATA_DIR/$d" "/app/$d"; fi' >> /app/start.sh && \
    echo '  done' >> /app/start.sh && \
    echo '  echo "Storing uploads and outputs in $DATA_DIR"' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Start Flask application' >> /app/start.sh && \
    echo 'echo "Starting Flask application on port $PORT..."' >> /app/start.sh && \
    echo 'cd /app && python run.py' >> /app/start.sh && \
    chmod +x /app/start.sh

# Expose port 80
EXPOSE 80

# Start the application
CMD ["/app/start.sh"]
