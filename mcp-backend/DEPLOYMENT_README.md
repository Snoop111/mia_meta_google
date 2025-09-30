# 🚀 Marketing Analytics MCP Server - Docker Deployment

Complete Docker deployment solution for your Marketing Analytics MCP Server.

## Quick Deploy (3 Commands)

```bash
# 1. Setup environment
cp .env.docker.example .env
# Edit .env with your API credentials

# 2. Deploy with one command
./scripts/deploy.sh

# 3. Complete OAuth setup
python verify_oauth_setup.py
```

## What You Get

### 🐳 Docker Infrastructure
- **Multi-stage build** with optimized layers
- **Non-root security** with dedicated app user  
- **Health checks** for container orchestration
- **Volume persistence** for credentials and logs
- **Resource limits** and monitoring ready

### 🌐 Deployment Options
1. **Docker Compose** (recommended for local/single-server)
2. **Google Cloud Run** (serverless, auto-scaling) 
3. **AWS ECS/Fargate** (managed containers)
4. **DigitalOcean App Platform** (simple PaaS)
5. **Any Docker-compatible host**

### 🔒 Production Ready
- **Environment-based secrets** management
- **SSL/TLS termination** with nginx proxy
- **Log aggregation** and monitoring hooks
- **Database persistence** options
- **Auto-restart** policies

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Claude Desktop │    │   Docker Host    │    │  Google APIs    │
│                 │    │ ┌──────────────┐ │    │                 │
│  MCP Client     │───▶│ │ Marketing    │ │───▶│ • Google Ads   │
│                 │    │ │ Analytics    │ │    │ • GA4          │
│                 │    │ │ Container    │ │    │ • OAuth        │
└─────────────────┘    │ └──────────────┘ │    └─────────────────┘
                       │ ┌──────────────┐ │
                       │ │ Nginx Proxy  │ │
                       │ │ (Optional)   │ │
                       │ └──────────────┘ │
                       └──────────────────┘
```

## File Structure

```
brain/
├── Dockerfile                          # Multi-stage container build
├── docker-compose.yml                  # Local deployment orchestration
├── .dockerignore                       # Build optimization
├── .env.docker.example                 # Environment template
├── scripts/deploy.sh                   # One-command deployment
├── deployment_guide.md                 # Complete deployment docs
├── cloud-deployments/                  # Cloud-specific configs
│   ├── gcp-cloud-run.yaml             # Google Cloud Run
│   ├── aws-ecs-task-definition.json    # AWS ECS/Fargate  
│   └── digitalocean-app.yaml           # DigitalOcean App Platform
└── claude_desktop_venv_config.json     # Claude Desktop MCP config
```

## Environment Variables

### Required
```env
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret  
GOOGLE_ADS_DEVELOPER_TOKEN=your_google_ads_developer_token
```

### Optional
```env
GA4_PROPERTY_ID=your_ga4_property_id
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
LOG_LEVEL=INFO
```

## Deployment Commands

### Local Development
```bash
docker-compose up -d                    # Start services
docker-compose logs -f                  # View logs
docker-compose down                     # Stop services
```

### Production Deployment
```bash
./scripts/deploy.sh deploy              # Full deployment
./scripts/deploy.sh status              # Check status
./scripts/deploy.sh restart             # Restart services
./scripts/deploy.sh cleanup             # Clean shutdown
```

### Cloud Deployment
```bash
# Google Cloud Run
gcloud run services replace cloud-deployments/gcp-cloud-run.yaml

# AWS ECS
aws ecs register-task-definition --cli-input-json file://cloud-deployments/aws-ecs-task-definition.json

# DigitalOcean
doctl apps create --spec cloud-deployments/digitalocean-app.yaml
```

## OAuth Setup Process

### 1. Start Container
```bash
./scripts/deploy.sh deploy
```

### 2. Verify OAuth
```bash
python verify_oauth_setup.py
# Follow browser OAuth flow when prompted
```

### 3. Configure Claude Desktop
```json
{
  "mcpServers": {
    "marketing-analytics": {
      "command": "/Users/martinstolk/Projects/Mia/brain/venv/bin/python",
      "args": ["/Users/martinstolk/Projects/Mia/brain/mcp_server.py"]
    }
  }
}
```

## Monitoring & Health

### Health Endpoints
```bash
curl http://localhost:8000/health       # FastAPI health
curl http://localhost:8000/docs         # API documentation
```

### Container Status
```bash
docker-compose ps                       # Service status
docker-compose top                      # Resource usage
docker stats marketing-analytics        # Real-time metrics
```

### Logs
```bash
docker-compose logs marketing-analytics # Application logs
docker-compose logs --tail=100 -f      # Live log streaming
```

## Security Features

- ✅ **Non-root container execution**
- ✅ **Minimal attack surface** (slim base image)
- ✅ **Environment-based secrets**
- ✅ **Network isolation** via Docker networks
- ✅ **Resource constraints** to prevent DoS
- ✅ **Health monitoring** for availability
- ✅ **SSL termination** ready

## Scaling Options

### Horizontal Scaling
```yaml
# docker-compose.yml
deploy:
  replicas: 3
```

### Load Balancing
```yaml
# With nginx reverse proxy
upstream backend {
  server marketing-analytics_1:8000;
  server marketing-analytics_2:8000;  
  server marketing-analytics_3:8000;
}
```

### Cloud Auto-scaling
- **Google Cloud Run**: Automatic based on requests
- **AWS ECS**: Target tracking scaling policies
- **DigitalOcean**: Horizontal pod autoscaling

## Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   docker-compose logs marketing-analytics
   ```

2. **OAuth redirect errors**
   - Check `GOOGLE_REDIRECT_URI` matches Google Console
   - Verify container port mapping

3. **API authentication failures**
   - Confirm all environment variables are set
   - Check credential expiration

4. **Performance issues**
   ```bash
   docker stats
   # Increase memory/CPU limits if needed
   ```

## Next Steps After Deployment

1. ✅ **Verify deployment**: `./scripts/deploy.sh status`
2. ✅ **Complete OAuth**: `python verify_oauth_setup.py`  
3. ✅ **Configure Claude Desktop** with MCP settings
4. ✅ **Test with Claude**: "Analyze my marketing performance"
5. 🚀 **Scale as needed** based on usage

Your Marketing Analytics MCP Server is now production-ready and scalable! 🎉

## Support

- 📖 **Full Documentation**: See `deployment_guide.md`
- 🐳 **Docker Issues**: Check container logs and health endpoints
- 🔑 **OAuth Problems**: Use `verify_oauth_setup.py` for debugging
- 🛠️ **MCP Integration**: Test with `test_mcp_server.py`