#!/bin/bash
# 🚀 One-Click Deploy - Minimal MCP Server (DigitalOcean builds it)
set -e

APP_NAME="marketing-analytics-mcp-minimal"

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

log "Creating minimal app spec for DigitalOcean build..."
cat > /tmp/minimal-buildpack.yaml << EOF
name: $APP_NAME
region: nyc1
services:
- name: mcp-api
  source_dir: /
  github:
    repo: $GITHUB_REPO
    branch: $CURRENT_BRANCH
    deploy_on_push: true
  dockerfile_path: Dockerfile.minimal
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

log "Deploying to DigitalOcean (they will build it)..."
doctl apps create --spec /tmp/minimal-buildpack.yaml --wait

APP_ID=$(doctl apps list --format ID,Name --no-header | grep "$APP_NAME" | awk '{print $1}')

echo ""
log "✅ DEPLOYMENT INITIATED!"
echo "📋 DigitalOcean is building your minimal MCP server..."
echo ""
echo "🔍 Check build status:"
echo "doctl apps get $APP_ID"
echo ""
echo "📊 View build logs:"
echo "doctl apps logs $APP_ID --follow"
echo ""
echo "🌐 Once live, your app will be at:"
echo "https://$APP_NAME.ondigitalocean.app"

rm -f /tmp/minimal-buildpack.yaml