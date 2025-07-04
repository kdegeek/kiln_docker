# Multi-stage build for Kiln AI application
# Build stage for web UI
FROM node:20-slim AS web-builder

WORKDIR /app/app/web_ui
# Copy web UI package files
COPY app/web_ui/package*.json ./
COPY app/web_ui/.npmrc ./
# Install Node.js dependencies including dev dependencies
RUN npm ci --include=dev
# Copy web UI source code
COPY app/web_ui/ ./
# Build the web UI
RUN npm run build

# Production stage
FROM python:3.12-slim

# Install system dependencies including sudo and common admin tools
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    sudo \
    net-tools \
    procps \
    htop \
    vim \
    iputils-ping \
    iproute2 \
    iptables \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Update CA certificates and configure SSL
RUN update-ca-certificates && \
    git config --global http.sslVerify false && \
    git config --global https.sslVerify false

# Install uv for Python dependency management with SSL bypass
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org uv

# Create non-root user and add to sudo group
RUN useradd --create-home --shell /bin/bash kiln && \
    usermod -aG sudo kiln && \
    echo "kiln ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

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

# Copy admin check script, startup script, and root test script
COPY admin_check.sh ./admin_check.sh
COPY start_server.sh ./start_server.sh
COPY test_root.sh ./test_root.sh
RUN chmod +x ./admin_check.sh ./start_server.sh ./test_root.sh

# Set appropriate permissions for both root and kiln user
RUN chown -R kiln:kiln /app && \
    chmod -R 755 /app && \
    # Ensure root can access all files
    chmod -R g+rwx /app && \
    # Add root to kiln group for file access
    usermod -aG kiln root

# Ensure container runs as root by default for administrator privileges
# This provides full system access within the container
# Root access is required for system-level operations and networking
USER root

# Expose the application port
EXPOSE 8757

# Set environment variables
ENV PYTHONPATH=/app
ENV KILN_SKIP_REMOTE_MODEL_LIST=false
ENV PYTHONHTTPSVERIFY=0
ENV SSL_VERIFY=0
# Ensure root privileges are maintained
ENV USER=root
ENV HOME=/root
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8757/ || exit 1

# Debug: Show directory structure and Python path
RUN echo "=== Directory structure ===" && \
    ls -la /app && \
    echo "=== App directory ===" && \
    ls -la /app/app && \
    echo "=== Desktop directory ===" && \
    ls -la /app/app/desktop && \
    echo "=== Python path ===" && \
    echo $PYTHONPATH

# Start the application using our startup script
CMD ["./start_server.sh"]