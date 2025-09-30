#!/bin/bash
# 🚀 Minimal Deploy - Just FastAPI Server First
# Get this working, then add MCP server

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_NAME="marketing-analytics-fastapi"

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║               🚀 MINIMAL DEPLOY SCRIPT 🚀                   ║
║                                                              ║
║  Deploys FastAPI Server (working first, then add MCP)       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

main() {
    print_banner
    
    log "Getting your API credentials..."
    
    read -p "🔑 Google OAuth Client ID: " GOOGLE_CLIENT_ID
    read -p "🔑 Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
    read -p "🔑 Google Ads Developer Token: " GOOGLE_ADS_DEVELOPER_TOKEN
    
    # Get GitHub info
    GITHUB_REPO=$(git remote get-url origin | sed 's/.*github.com[\/:]//; s/\.git$//')
    CURRENT_BRANCH=$(git branch --show-current)
    
    log "Repo: $GITHUB_REPO, Branch: $CURRENT_BRANCH"
    
    # Create minimal app spec
    cat > /tmp/minimal-app.yaml << EOF
name: ${APP_NAME}
region: nyc1
services:
- name: fastapi-server
  source_dir: /
  github:
    repo: ${GITHUB_REPO}
    branch: ${CURRENT_BRANCH}
  build_command: pip install -r requirements-data-apis.txt
  run_command: uvicorn main:app --host 0.0.0.0 --port 8080
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-s
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 30
    timeout_seconds: 10
  envs:
  - key: GOOGLE_CLIENT_ID
    value: "${GOOGLE_CLIENT_ID}"
    type: SECRET
  - key: GOOGLE_CLIENT_SECRET
    value: "${GOOGLE_CLIENT_SECRET}"
    type: SECRET
  - key: GOOGLE_ADS_DEVELOPER_TOKEN
    value: "${GOOGLE_ADS_DEVELOPER_TOKEN}"
    type: SECRET
  - key: PYTHONPATH
    value: "/app"
EOF
    
    log "Deploying minimal FastAPI server..."
    
    doctl apps create --spec /tmp/minimal-app.yaml --wait
    
    APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
    APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header 2>/dev/null || echo "https://${APP_NAME}.ondigitalocean.app")
    
    echo ""
    echo -e "${GREEN}🎉 FastAPI Server Deployed! 🎉${NC}"
    echo "🌐 URL: $APP_URL"
    echo "📖 Docs: $APP_URL/docs"
    echo "🔍 Health: $APP_URL/health"
    echo ""
    echo "📋 Complete OAuth setup:"
    echo "curl $APP_URL/google-oauth/auth-url"
    echo ""
    echo "🛠️ View logs: doctl apps logs $APP_ID --follow"
    
    rm -f /tmp/minimal-app.yaml
}

main "$@"