# Kiln AI - Docker Image

[![Docker Image Version](https://img.shields.io/docker/v/kdegeek/kiln-ai?sort=semver)](https://hub.docker.com/r/kdegeek/kiln-ai)
[![Docker Image Size](https://img.shields.io/docker/image-size/kdegeek/kiln-ai/latest)](https://hub.docker.com/r/kdegeek/kiln-ai)
[![Docker Pulls](https://img.shields.io/docker/pulls/kdegeek/kiln-ai)](https://hub.docker.com/r/kdegeek/kiln-ai)

Kiln AI is a comprehensive toolkit for creating, managing, and optimizing AI datasets and models. This Docker image provides a containerized deployment for production environments or isolated development setups.

## Quick Start

```bash
# Run Kiln AI with Docker
docker run -p 8757:8757 kdegeek/kiln-ai:latest
```

Then open http://localhost:8757 in your browser.

## Features

- **Multi-stage Build**: Optimized for production with minimal image size
- **Security**: Runs as non-root user with minimal system dependencies  
- **Health Checks**: Built-in health monitoring
- **Multi-platform**: Supports both AMD64 and ARM64 architectures

## Available Tags

- `latest` - Latest stable release from main branch
- `v*` - Specific version releases (e.g., `v1.0.0`, `v1.1.0`)
- `main` - Latest development build from main branch

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KILN_HOST` | `0.0.0.0` | Host interface to bind to |
| `KILN_PORT` | `8757` | Port to listen on |
| `KILN_LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `KILN_SKIP_REMOTE_MODEL_LIST` | `false` | Skip loading remote model configurations |

### Volume Mounts

For persistent data, mount directories:

```bash
docker run -p 8757:8757 \
  -v $(pwd)/kiln-data:/app/data \
  -v $(pwd)/datasets:/app/datasets \
  kdegeek/kiln-ai:latest
```

### Docker Compose

```yaml
services:
  kiln:
    image: kdegeek/kiln-ai:latest
    ports:
      - "8757:8757"
    environment:
      - KILN_HOST=0.0.0.0
      - KILN_PORT=8757
      - KILN_LOG_LEVEL=info
    volumes:
      - ./kiln-data:/app/data
      - ./datasets:/app/datasets
    restart: unless-stopped
```

## Documentation

For complete documentation, visit: https://github.com/kdegeek/kiln_docker

## Support

- GitHub Issues: https://github.com/Kiln-AI/kiln/issues
- Documentation: https://github.com/kdegeek/kiln_docker/blob/main/DOCKER.md

## License

This Docker configuration is part of the Kiln AI project and follows the same license terms.