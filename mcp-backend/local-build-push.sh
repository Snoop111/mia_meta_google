#!/bin/bash
# Build locally and push to DigitalOcean Container Registry
set -e

APP_NAME="marketing-analytics-mcp"
REGISTRY="registry.digitalocean.com"
REGION="nyc1"

log() { echo "🚀 $1"; }
error() { echo "❌ $1"; exit 1; }

log "Building Docker image locally with full requirements..."
docker build -t $APP_NAME --platform linux/amd64 .

log "Getting DigitalOcean registry login..."
doctl registry login

log "Tagging image for registry..."
docker tag $APP_NAME $REGISTRY/$APP_NAME/$APP_NAME:latest

log "Pushing to DigitalOcean Container Registry..."
docker push $REGISTRY/$APP_NAME/$APP_NAME:latest

log "Creating app spec for container registry deployment..."
cat > /tmp/container-app.yaml << EOF
name: $APP_NAME
region: $REGION
services:
- name: api
  image:
    registry_type: DOCR
    repository: $APP_NAME
    tag: latest
  instance_count: 1
  instance_size_slug: basic-s
  http_port: 8080
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 30
    timeout_seconds: 10
  envs:
  - key: GOOGLE_CLIENT_ID
    value: "$GOOGLE_CLIENT_ID"
    type: SECRET
  - key: GOOGLE_CLIENT_SECRET
    value: "$GOOGLE_CLIENT_SECRET" 
    type: SECRET
  - key: GOOGLE_ADS_DEVELOPER_TOKEN
    value: "$GOOGLE_ADS_DEVELOPER_TOKEN"
    type: SECRET
  - key: PYTHONPATH
    value: "/app"
EOF

read -p "🔑 Google OAuth Client ID: " GOOGLE_CLIENT_ID
read -p "🔑 Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
read -p "🔑 Google Ads Developer Token: " GOOGLE_ADS_DEVELOPER_TOKEN

# Update the spec with credentials
sed -i '' "s/\$GOOGLE_CLIENT_ID/$GOOGLE_CLIENT_ID/g" /tmp/container-app.yaml
sed -i '' "s/\$GOOGLE_CLIENT_SECRET/$GOOGLE_CLIENT_SECRET/g" /tmp/container-app.yaml  
sed -i '' "s/\$GOOGLE_ADS_DEVELOPER_TOKEN/$GOOGLE_ADS_DEVELOPER_TOKEN/g" /tmp/container-app.yaml

log "Deploying from container registry..."
doctl apps create --spec /tmp/container-app.yaml --wait

APP_ID=$(doctl apps list --format ID,Name --no-header | grep "$APP_NAME" | awk '{print $1}')
APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header 2>/dev/null || echo "https://$APP_NAME.ondigitalocean.app")

log "✅ DEPLOYED! URL: $APP_URL"
log "📖 Docs: $APP_URL/docs"
log "🔍 Health: $APP_URL/health"

rm -f /tmp/container-app.yaml