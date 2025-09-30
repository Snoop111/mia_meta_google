# Marketing Analytics MCP Server - Deployment Guide

Complete guide for deploying your Marketing Analytics MCP server using Docker in various environments.

## Quick Start (Docker Compose)

### 1. Prepare Environment
```bash
# Clone/navigate to your project
cd /Users/martinstolk/Projects/Mia/brain

# Copy environment template
cp .env.docker.example .env

# Edit with your actual API credentials
nano .env
```

### 2. Build and Run
```bash
# Build and start the container
docker-compose up -d

# Check logs
docker-compose logs -f marketing-analytics

# Test the deployment
curl http://localhost:8000/docs
```

### 3. Complete OAuth Setup
```bash
# Run OAuth verification (inside container)
docker-compose exec marketing-analytics python verify_oauth_setup.py

# Or test from host
python verify_oauth_setup.py
```

## Deployment Options

### Option 1: Simple Docker (Development/Testing)

```bash
# Build image
docker build -t marketing-analytics-mcp .

# Run container
docker run -d \
  --name marketing-analytics \
  -p 8000:8000 \
  -p 8001:8001 \
  -e GOOGLE_CLIENT_ID="your_client_id" \
  -e GOOGLE_CLIENT_SECRET="your_client_secret" \
  -e GOOGLE_ADS_DEVELOPER_TOKEN="your_dev_token" \
  -v $(pwd)/data:/app/data \
  marketing-analytics-mcp
```

### Option 2: Docker Compose (Recommended)

**Basic deployment:**
```bash
docker-compose up -d
```

**Production with reverse proxy:**
```bash
docker-compose --profile production up -d
```

**With PostgreSQL database:**
```bash
docker-compose --profile database up -d
```

### Option 3: Cloud Deployment

#### Google Cloud Run
```bash
# Build and push to Google Container Registry
docker build -t gcr.io/your-project/marketing-analytics-mcp .
docker push gcr.io/your-project/marketing-analytics-mcp

# Deploy to Cloud Run
gcloud run deploy marketing-analytics \
  --image gcr.io/your-project/marketing-analytics-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLIENT_ID=your_client_id" \
  --set-env-vars="GOOGLE_CLIENT_SECRET=your_client_secret" \
  --set-env-vars="GOOGLE_ADS_DEVELOPER_TOKEN=your_dev_token" \
  --port 8000
```

#### AWS ECS/Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com
docker build -t marketing-analytics-mcp .
docker tag marketing-analytics-mcp:latest your-account.dkr.ecr.us-east-1.amazonaws.com/marketing-analytics-mcp:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/marketing-analytics-mcp:latest

# Deploy using ECS task definition (see ecs-task-definition.json)
```

#### DigitalOcean App Platform
```bash
# Create app.yaml and deploy
doctl apps create --spec app.yaml
```

## Configuration Files

### Environment Variables (.env)
```env
# Required
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_ADS_DEVELOPER_TOKEN=your_google_ads_developer_token

# Optional
GA4_PROPERTY_ID=your_ga4_property_id
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
LOG_LEVEL=INFO

# Production
DB_PASSWORD=secure_database_password
```

### Nginx Configuration (nginx.conf)
```nginx
events {
    worker_connections 1024;
}

http {
    upstream marketing_backend {
        server marketing-analytics:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://marketing_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## Deployment Architectures

### 1. Single Container (Simple)
```
┌─────────────────┐
│  Docker Host    │
│ ┌─────────────┐ │
│ │ Marketing   │ │
│ │ Analytics   │ │
│ │ Container   │ │
│ │ :8000,:8001 │ │
│ └─────────────┘ │
└─────────────────┘
```

### 2. Multi-Container with Proxy (Production)
```
┌───────────────────────────────────┐
│            Docker Host            │
│ ┌─────────┐  ┌─────────────────┐  │
│ │ Nginx   │  │ Marketing       │  │
│ │ Proxy   │─▶│ Analytics       │  │
│ │ :80,:443│  │ Container       │  │
│ └─────────┘  └─────────────────┘  │
│              ┌─────────────────┐  │
│              │ PostgreSQL      │  │
│              │ Database        │  │
│              └─────────────────┘  │
└───────────────────────────────────┘
```

### 3. Cloud Native (Scalable)
```
┌─────────────────────────────────────┐
│           Cloud Provider            │
│ ┌─────────────┐ ┌─────────────────┐ │
│ │ Load        │ │ Container       │ │
│ │ Balancer    │─┤ Instances       │ │
│ │             │ │ (Auto Scaling)  │ │
│ └─────────────┘ └─────────────────┘ │
│                 ┌─────────────────┐ │
│                 │ Managed         │ │
│                 │ Database        │ │
│                 └─────────────────┘ │
└─────────────────────────────────────┘
```

## Security Considerations

### Container Security
```dockerfile
# Use non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Read-only filesystem (add to docker-compose.yml)
read_only: true
tmpfs:
  - /tmp
  - /app/logs
```

### Environment Security
```bash
# Use Docker secrets for sensitive data
echo "your_secret" | docker secret create google_client_secret -

# Or use external secret management
# - AWS Secrets Manager
# - Google Secret Manager  
# - HashiCorp Vault
```

### Network Security
```yaml
# docker-compose.yml security additions
services:
  marketing-analytics:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
```

## Monitoring and Logging

### Health Checks
```bash
# Container health
docker-compose ps

# Application health
curl http://localhost:8000/health

# MCP server status
python test_mcp_server.py
```

### Logging Setup
```yaml
# docker-compose.yml logging
services:
  marketing-analytics:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring Integration
```yaml
# Add monitoring services
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

## Scaling and Performance

### Horizontal Scaling
```yaml
# docker-compose.yml with scaling
services:
  marketing-analytics:
    deploy:
      replicas: 3
    
  nginx:
    depends_on:
      - marketing-analytics
```

### Resource Limits
```yaml
# Resource constraints
services:
  marketing-analytics:
    mem_limit: 2g
    cpus: 1.0
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
docker-compose exec marketing-analytics cp /app/data/credentials.db /app/data/backup/

# PostgreSQL backup
docker-compose exec postgres pg_dump -U marketing marketing_analytics > backup.sql
```

### Volume Backup
```bash
# Backup persistent data
docker run --rm -v marketing_data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz /data
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   docker-compose logs marketing-analytics
   docker-compose exec marketing-analytics python -c "import sys; print(sys.path)"
   ```

2. **OAuth not working**
   ```bash
   # Check redirect URI in Google Console matches container URL
   # Verify environment variables
   docker-compose exec marketing-analytics env | grep GOOGLE
   ```

3. **MCP server not accessible**
   ```bash
   # Test MCP server directly
   docker-compose exec marketing-analytics python test_mcp_server.py
   
   # Check network connectivity
   docker network ls
   docker network inspect brain_marketing-network
   ```

4. **Performance issues**
   ```bash
   # Monitor resources
   docker stats
   docker-compose top
   
   # Check logs for bottlenecks
   docker-compose logs --tail=100 marketing-analytics
   ```

## Production Checklist

- [ ] Environment variables set in `.env` file
- [ ] SSL certificates configured (if using HTTPS)
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] Health checks working
- [ ] Resource limits set
- [ ] Security policies applied
- [ ] Monitoring setup
- [ ] OAuth callback URLs updated for production domain
- [ ] Firewall rules configured
- [ ] DNS records pointing to deployment

## Client Configuration

### Claude Desktop (Docker Deployment)
```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "docker",
      "args": ["exec", "marketing-analytics-mcp", "python", "/app/mcp_server.py"],
      "env": {}
    }
  }
}
```

### Remote MCP Access
```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "python",
      "args": ["/path/to/remote_mcp_client.py"],
      "env": {
        "MCP_SERVER_URL": "http://your-domain.com:8001"
      }
    }
  }
}
```

Your Marketing Analytics MCP server is now ready for production deployment! 🚀