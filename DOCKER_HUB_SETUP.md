# Docker Hub Setup Guide

This guide explains how to configure Docker Hub publishing for the Kiln AI project.

## Prerequisites

1. **Docker Hub Account**: Create a free account at [hub.docker.com](https://hub.docker.com)
2. **Docker Hub Repository**: Create a repository named `kiln-ai` in your Docker Hub account
3. **GitHub Repository Secrets**: Configure the required secrets in your GitHub repository

## Setting up Docker Hub Repository

1. **Login to Docker Hub**: Go to [hub.docker.com](https://hub.docker.com) and sign in
2. **Create Repository**: 
   - Click "Create Repository"
   - Repository Name: `kiln-ai`
   - Visibility: Public (recommended) or Private
   - Description: "Kiln AI - Comprehensive toolkit for AI datasets and models"
3. **Configure Repository**:
   - Set up the repository description using the content from `DOCKERHUB.md`
   - Add relevant tags: `ai`, `machine-learning`, `datasets`, `docker`, `python`

## Setting up GitHub Secrets

The GitHub Actions workflow requires two secrets to be configured in your repository:

### Required Secrets

1. **DOCKERHUB_USERNAME**
   - Value: Your Docker Hub username
   - Example: `kdegeek`

2. **DOCKERHUB_TOKEN**
   - Value: A Docker Hub access token (not your password)
   - How to create:
     1. Go to Docker Hub → Account Settings → Security
     2. Click "New Access Token"
     3. Description: "GitHub Actions for kiln_docker"
     4. Permissions: Read, Write, Delete
     5. Copy the generated token

### Configuring Secrets in GitHub

1. **Navigate to Repository Settings**:
   - Go to your GitHub repository
   - Click "Settings" → "Secrets and variables" → "Actions"

2. **Add Repository Secrets**:
   - Click "New repository secret"
   - Add `DOCKERHUB_USERNAME` with your Docker Hub username
   - Add `DOCKERHUB_TOKEN` with your access token

## Workflow Triggers

The Docker publishing workflow will automatically trigger on:

1. **Push to main branch**: Creates `latest` and `main` tags
2. **Version tags**: Creates version-specific tags (e.g., `v1.0.0`, `v1.1.0`)
3. **Pull requests**: Builds images but doesn't push (for testing)

## Available Docker Image Tags

Once the workflow runs successfully, the following tags will be available:

- `kdegeek/kiln-ai:latest` - Latest stable release
- `kdegeek/kiln-ai:main` - Latest development build
- `kdegeek/kiln-ai:v1.0.0` - Specific version releases

## Verification

After setting up the secrets and triggering a workflow run:

1. **Check GitHub Actions**: Verify the workflow completes successfully
2. **Check Docker Hub**: Confirm images are published to your repository
3. **Test the image**: Pull and run the published image

```bash
# Test the published image
docker pull kdegeek/kiln-ai:latest
docker run -p 8757:8757 kdegeek/kiln-ai:latest
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Check that secrets are correctly configured
2. **Repository Not Found**: Ensure the Docker Hub repository exists
3. **Permission Denied**: Verify the access token has write permissions
4. **Build Failures**: Check the GitHub Actions logs for specific errors

### Updating Repository Description

The workflow automatically updates the Docker Hub repository description using `DOCKERHUB.md`. If you need to manually update it:

1. Edit `DOCKERHUB.md` in the repository
2. Push changes to the main branch
3. The next workflow run will update the description

## Security Considerations

- **Access Token Scope**: Use the minimum required permissions (Read, Write, Delete)
- **Token Rotation**: Regularly rotate access tokens for security
- **Secret Management**: Never commit tokens or passwords to the repository
- **Repository Visibility**: Consider making the Docker Hub repository public for easier access

## Multi-platform Builds

The workflow is configured to build for multiple platforms:
- `linux/amd64` - Intel/AMD 64-bit processors
- `linux/arm64` - ARM 64-bit processors (Apple Silicon, ARM servers)

This ensures compatibility across different deployment environments.