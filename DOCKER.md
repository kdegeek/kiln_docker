# Docker Deployment for Kiln AI

This directory contains Docker configuration files to containerize and deploy the Kiln AI application.

## Quick Start

### Using Docker

1. **Build the Docker image:**
   ```bash
   docker build -t kiln-ai .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8757:8757 kiln-ai
   ```

3. **Access the application:**
   - Web UI: http://localhost:8757
   - API: http://localhost:8757/api

### Using Docker Compose (Recommended)

1. **Start the application:**
   ```bash
   docker compose up -d
   ```

2. **View logs:**
   ```bash
   docker compose logs -f
   ```

3. **Stop the application:**
   ```bash
   docker compose down
   ```

## Configuration

### Environment Variables

The following environment variables can be configured:

| Variable | Default | Description |
|----------|---------|-------------|
| `KILN_HOST` | `0.0.0.0` | Host interface to bind to |
| `KILN_PORT` | `8757` | Port to listen on |
| `KILN_LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `KILN_SKIP_REMOTE_MODEL_LIST` | `false` | Skip loading remote model configurations |

### Volume Mounts

For persistent data, you can mount directories:

```bash
docker run -p 8757:8757 \
  -v $(pwd)/kiln-data:/app/data \
  -v $(pwd)/datasets:/app/datasets \
  kiln-ai
```

Or update the `docker-compose.yml` file to uncomment the volume sections.

## Docker Image Details

### Multi-stage Build

The Dockerfile uses a multi-stage build process:

1. **Web Builder Stage**: Builds the Svelte/TypeScript web UI using Node.js 20
2. **Production Stage**: Creates the runtime environment with Python 3.12 and serves both API and web UI

### Image Size Optimization

- Uses `python:3.12-slim` as the base image
- Removes build dependencies after installation
- Excludes development files via `.dockerignore`
- Runs as non-root user for security

### Security Features

- Non-root user execution
- Minimal system dependencies
- Health check configuration
- SSL certificate handling for containerized environments

## Troubleshooting

### SSL Certificate Issues

The container includes SSL certificate workarounds for environments with certificate verification issues. If you encounter SSL-related errors, ensure the following environment variables are set:

```bash
PYTHONHTTPSVERIFY=0
SSL_VERIFY=0
```

### Port Conflicts

If port 8757 is already in use, you can map to a different port:

```bash
docker run -p 8080:8757 kiln-ai
```

### Memory Usage

For large datasets or high concurrency, you may need to adjust memory limits:

```bash
docker run -p 8757:8757 --memory=4g kiln-ai
```

### Health Check

The container includes a health check that verifies the web server is responding:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' <container_id>
```

## Development

### Building for Development

To build with different configurations:

```bash
# Build with development dependencies
docker build --target development -t kiln-ai:dev .

# Build with custom build args
docker build --build-arg PYTHON_VERSION=3.11 -t kiln-ai:py311 .
```

### Testing the Container

After building, you can test the container:

```bash
# Run tests against the container
docker run --rm kiln-ai python -m pytest

# Interactive shell for debugging
docker run -it --entrypoint /bin/bash kiln-ai
```

## Publishing to DockerHub

To publish the image to DockerHub:

1. **Tag the image:**
   ```bash
   docker tag kiln-ai your-dockerhub-username/kiln-ai:latest
   docker tag kiln-ai your-dockerhub-username/kiln-ai:v1.0.0
   ```

2. **Push to DockerHub:**
   ```bash
   docker push your-dockerhub-username/kiln-ai:latest
   docker push your-dockerhub-username/kiln-ai:v1.0.0
   ```

3. **Pull and run from DockerHub:**
   ```bash
   docker run -p 8757:8757 your-dockerhub-username/kiln-ai:latest
   ```

## License

This Docker configuration is part of the Kiln AI project and follows the same license terms.