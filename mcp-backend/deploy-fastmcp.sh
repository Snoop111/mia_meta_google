#!/bin/bash
# 🚀 One-Click Deploy - FastMCP (Single service with MCP integrated)
set -e

APP_NAME="marketing-analytics-fastmcp"

log() { echo "🚀 $1"; }

log "Collecting credentials..."
read -p "🔑 Google OAuth Client ID: " GOOGLE_CLIENT_ID
read -p "🔑 Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
read -p "🔑 Google Ads Developer Token: " GOOGLE_ADS_DEVELOPER_TOKEN

# Get GitHub repo and branch
GITHUB_REPO=$(git remote get-url origin | sed 's/.*github.com[\/:]//; s/\.git$//')
CURRENT_BRANCH=$(git branch --show-current)

log "GitHub repo: $GITHUB_REPO"
log "Branch: $CURRENT_BRANCH"

log "Creating FastMCP app spec for DigitalOcean build..."
cat > /tmp/fastmcp-app.yaml << EOF
name: $APP_NAME
region: nyc1
services:
- name: fastmcp-api
  source_dir: /
  github:
    repo: $GITHUB_REPO
    branch: $CURRENT_BRANCH
    deploy_on_push: true
  dockerfile_path: Dockerfile.fastmcp
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-xxs
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

log "Deploying FastMCP server (single service)..."
doctl apps create --spec /tmp/fastmcp-app.yaml --wait

APP_ID=$(doctl apps list --format ID,Name --no-header | grep "$APP_NAME" | awk '{print $1}')

echo ""
log "✅ FASTMCP DEPLOYMENT INITIATED!"
echo "📋 DigitalOcean is building your FastMCP server..."
echo ""
echo "🔍 Check build status:"
echo "doctl apps get $APP_ID"
echo ""
echo "📊 View build logs:"
echo "doctl apps logs $APP_ID --follow"
echo ""
echo "🌐 Once live, your app will be at:"
echo "https://$APP_NAME.ondigitalocean.app"
echo ""
echo "🎯 For your MCP agent:"
echo "FastAPI URL: https://$APP_NAME.ondigitalocean.app"
echo "MCP Endpoint: https://$APP_NAME.ondigitalocean.app/mcp"
echo ""
echo "📋 Available tools:"
echo "- comprehensive_insights"
echo "- campaign_analysis" 
echo "- setup_credentials"

rm -f /tmp/fastmcp-app.yaml