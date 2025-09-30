#!/bin/bash
set -e

# DigitalOcean Apps Platform Deployment with Local Docker Build
# Builds Docker image locally, pushes to DO Container Registry, deploys to Apps Platform

APP_NAME="marketing-analytics-mcp"
REGION="nyc3"
IMAGE_NAME="brain-fastmcp"
REGISTRY_NAME="marketing-registry"

echo "🚀 Deploying Marketing Analytics with FastMCP to DigitalOcean..."

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI is not installed. Please install it first:"
    echo "   Visit: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if user is authenticated
if ! doctl account get &> /dev/null; then
    echo "❌ Not authenticated with DigitalOcean. Please run:"
    echo "   doctl auth init"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Step 1/5: Building Docker image locally for linux/amd64..."
# Force rebuild without cache to ensure latest changes
docker build --platform linux/amd64 --no-cache -t $IMAGE_NAME .

log "Step 2/5: Creating/configuring container registry..."
# Create registry if it doesn't exist
doctl registry create $REGISTRY_NAME || echo "Registry may already exist"

# Get registry info  
REGISTRY_URL="registry.digitalocean.com/$REGISTRY_NAME"

log "Step 3/5: Pushing Docker image to registry..."
# Use timestamp tag to avoid cache issues
TIMESTAMP=$(date +%s)
NEW_TAG="latest-$TIMESTAMP"

# Tag and push image with new tag
docker tag $IMAGE_NAME "$REGISTRY_URL/$IMAGE_NAME:$NEW_TAG"
docker tag $IMAGE_NAME "$REGISTRY_URL/$IMAGE_NAME:latest"
doctl registry login
docker push "$REGISTRY_URL/$IMAGE_NAME:$NEW_TAG"
docker push "$REGISTRY_URL/$IMAGE_NAME:latest"

log "Pushed image with tags: latest and $NEW_TAG"

log "Step 4/5: Creating app spec for container deployment..."
# Load environment variables for deployment
if [ -f .env ]; then
    source .env
fi

cat > app-spec.yaml << EOF
name: $APP_NAME
services:
- name: brain-api
  image:
    registry_type: DOCR
    registry: $REGISTRY_NAME
    repository: $IMAGE_NAME
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
  health_check:
    http_path: /health
  envs:
  - key: GOOGLE_CLIENT_ID
    value: "${GOOGLE_CLIENT_ID}"
  - key: GOOGLE_CLIENT_SECRET
    value: "${GOOGLE_CLIENT_SECRET}"
  - key: GOOGLE_ADS_DEVELOPER_TOKEN
    value: "${GOOGLE_ADS_DEVELOPER_TOKEN}"
  - key: GOOGLE_REDIRECT_URI
    value: "${GOOGLE_REDIRECT_URI}"
  - key: GA4_PROPERTY_ID
    value: "${GA4_PROPERTY_ID}"
  - key: META_CLIENT_ID
    value: "${META_CLIENT_ID}"
  - key: META_CLIENT_SECRET
    value: "${META_CLIENT_SECRET}"
  - key: GOOGLE_APPLICATION_CREDENTIALS
    value: "${GOOGLE_APPLICATION_CREDENTIALS}"
  - key: META_REDIRECT_URI
    value: "${META_REDIRECT_URI}"
  routes:
  - path: /
EOF

log "Step 5/5: Deploying to DigitalOcean Apps Platform..."

# Check if app exists
if doctl apps list | grep -q "$APP_NAME"; then
    log "Updating existing app..."
    APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | grep "$APP_NAME" | cut -d' ' -f1)
    doctl apps update "$APP_ID" --spec app-spec.yaml
    
    # Force deployment to pull latest image
    log "Forcing deployment to pull latest image..."
    doctl apps create-deployment "$APP_ID" --force-rebuild
else
    log "Creating new app..."
    doctl apps create --spec app-spec.yaml
fi

log "✅ Deployment initiated!"
echo ""
echo "📋 Your app is being deployed to DigitalOcean Apps Platform"
echo "🔗 You'll get a URL like: https://$APP_NAME-xxxxx.ondigitalocean.app"
echo "📊 MCP Tools: Available via FastMCP integration at /tools"
echo "🔒 SSL: Automatically provisioned by DigitalOcean"
echo ""
echo "Monitor deployment with: doctl apps list"
echo "View logs with: doctl apps logs <app-id> --follow"