#!/bin/bash
# 🚀 One-Click Deploy - Minimal MCP Server (No ML libraries)
set -e

APP_NAME="marketing-analytics-mcp-minimal"
REGISTRY="registry.digitalocean.com"

log() { echo "🚀 $1"; }

log "Building minimal Docker image locally..."
docker build -t $APP_NAME --platform linux/amd64 -f Dockerfile.minimal .

log "Getting DigitalOcean registry login..."
doctl registry login

log "Tagging image for registry..."
docker tag $APP_NAME $REGISTRY/$APP_NAME/$APP_NAME:latest

log "Pushing to DigitalOcean Container Registry..."
docker push $REGISTRY/$APP_NAME/$APP_NAME:latest

log "Collecting credentials..."
read -p "🔑 Google OAuth Client ID: " GOOGLE_CLIENT_ID
read -p "🔑 Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
read -p "🔑 Google Ads Developer Token: " GOOGLE_ADS_DEVELOPER_TOKEN

log "Creating minimal app spec..."
cat > /tmp/minimal-app.yaml << EOF
name: $APP_NAME
region: nyc1
services:
- name: mcp-api
  image:
    registry_type: DOCR
    repository: $APP_NAME
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8080
  health_check:
    http_path: /health
    initial_delay_seconds: 30
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

log "Deploying minimal MCP server..."
doctl apps create --spec /tmp/minimal-app.yaml --wait

APP_ID=$(doctl apps list --format ID,Name --no-header | grep "$APP_NAME" | awk '{print $1}')
APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header 2>/dev/null || echo "https://$APP_NAME.ondigitalocean.app")

echo ""
log "✅ MINIMAL MCP SERVER DEPLOYED!"
echo "🌐 FastAPI: $APP_URL"
echo "📖 Docs: $APP_URL/docs"
echo "🔍 Health: $APP_URL/health"
echo "🤖 MCP Port: 8001 (internal)"
echo ""
echo "🎯 For your MCP agent:"
echo "URL: $APP_URL:8001"
echo "Protocol: JSON-RPC over HTTP"
echo ""
echo "📋 Available MCP tools:"
echo "- comprehensive_insights"
echo "- campaign_analysis" 
echo "- setup_credentials"

rm -f /tmp/minimal-app.yaml