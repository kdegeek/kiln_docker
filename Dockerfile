# Multi-stage build for Kiln AI application
# Build stage for web UI
FROM node:20-slim AS web-builder

WORKDIR /app/app/web_ui
# Copy web UI package files
COPY app/web_ui/package*.json ./
# Install Node.js dependencies
RUN npm ci
# Copy web UI source code
COPY app/web_ui/ ./
# Build the web UI
RUN npm run build

# Production stage
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Update CA certificates and configure SSL
RUN update-ca-certificates && \
    git config --global http.sslVerify false && \
    git config --global https.sslVerify false

# Install uv for Python dependency management with SSL bypass
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org uv

# Create non-root user
RUN useradd --create-home --shell /bin/bash kiln

# Set working directory
WORKDIR /app

# Copy Python project files
COPY pyproject.toml uv.lock ./
COPY libs/ ./libs/
COPY app/desktop/ ./app/desktop/
COPY app/__init__.py ./app/

# Set additional SSL environment variables for Python
ENV PYTHONHTTPSVERIFY=0
ENV SSL_VERIFY=false

# Install Python dependencies with comprehensive SSL bypass
RUN uv sync --frozen --no-dev --no-cache --index-url https://pypi.org/simple/ --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Copy built web UI from build stage
COPY --from=web-builder /app/app/web_ui/build ./app/web_ui/build/

# Change ownership to non-root user
RUN chown -R kiln:kiln /app

# Switch to non-root user
USER kiln

# Expose the application port
EXPOSE 8757

# Set environment variables
ENV PYTHONPATH=/app
ENV KILN_SKIP_REMOTE_MODEL_LIST=false
ENV PYTHONHTTPSVERIFY=0
ENV SSL_VERIFY=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8757/ || exit 1

# Start the application
CMD ["uv", "run", "python", "app/desktop/server_runner.py"]