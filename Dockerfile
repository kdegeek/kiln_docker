# Single-stage build for Kiln AI application
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for Python dependency management
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

# Install Python dependencies
RUN git config --global http.sslVerify false && \
    git config --global https.sslVerify false && \
    uv sync --frozen --no-dev --no-cache

# Copy web UI files and build
COPY app/web_ui/ ./app/web_ui/
WORKDIR /app/app/web_ui
RUN npm ci --only=production=false && npm run build

# Go back to app directory
WORKDIR /app

# Change ownership to non-root user
RUN chown -R kiln:kiln /app

# Switch to non-root user
USER kiln

# Expose the application port
EXPOSE 8757

# Set environment variables
ENV PYTHONPATH=/app
ENV KILN_SKIP_REMOTE_MODEL_LIST=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8757/ || exit 1

# Start the application
CMD ["uv", "run", "python", "app/desktop/server_runner.py"]