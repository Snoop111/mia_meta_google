#!/bin/bash
# 🚀 One-Click Deploy Script for Marketing Analytics MCP Server
# Deploys both FastAPI (OAuth) and MCP Server to DigitalOcean App Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_NAME="marketing-analytics-mcp"
GITHUB_REPO="mrtnstolk/marketing-analytics-mcp"  # Update this
REGION="nyc1"

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║               🚀 ONE-CLICK DEPLOY SCRIPT 🚀                 ║
║                                                              ║
║  Deploys Marketing Analytics MCP Server to DigitalOcean     ║
║  ✅ FastAPI Server (OAuth + API)                            ║
║  ✅ MCP Server (Claude integration)                         ║
║  ✅ Automatic HTTPS & scaling                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

check_requirements() {
    log "Checking requirements..."
    
    # Check doctl CLI
    if ! command -v doctl &> /dev/null; then
        warn "DigitalOcean CLI not found. Installing..."
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            brew install doctl || {
                error "Please install doctl: brew install doctl"
            }
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            wget https://github.com/digitalocean/doctl/releases/latest/download/doctl-1.94.0-linux-amd64.tar.gz
            tar xf doctl-*-linux-amd64.tar.gz
            sudo mv doctl /usr/local/bin
        else
            error "Please install doctl CLI: https://docs.digitalocean.com/reference/doctl/how-to/install/"
        fi
    fi
    
    # Check if logged in
    if ! doctl account get >/dev/null 2>&1; then
        warn "Not logged in to DigitalOcean. Please authenticate:"
        doctl auth init
    fi
    
    log "Requirements check passed ✅"
}

collect_credentials() {
    log "Collecting API credentials..."
    
    echo -e "${BLUE}You'll need the following credentials:${NC}"
    echo "1. Google OAuth Client ID"
    echo "2. Google OAuth Client Secret" 
    echo "3. Google Ads Developer Token"
    echo "4. GA4 Property ID (optional)"
    echo ""
    
    read -p "🔑 Google OAuth Client ID: " GOOGLE_CLIENT_ID
    read -p "🔑 Google OAuth Client Secret: " GOOGLE_CLIENT_SECRET
    read -p "🔑 Google Ads Developer Token: " GOOGLE_ADS_DEVELOPER_TOKEN
    read -p "📊 GA4 Property ID (optional): " GA4_PROPERTY_ID
    
    if [[ -z "$GOOGLE_CLIENT_ID" || -z "$GOOGLE_CLIENT_SECRET" || -z "$GOOGLE_ADS_DEVELOPER_TOKEN" ]]; then
        error "Required credentials missing. Please provide all required values."
    fi
    
    log "Credentials collected ✅"
}

create_app_spec() {
    log "Creating app specification..."
    
    # Get the actual GitHub repo if in git directory
    if git remote -v >/dev/null 2>&1; then
        GITHUB_REPO=$(git remote get-url origin | sed 's/.*github.com[\/:]//; s/\.git$//')
        CURRENT_BRANCH=$(git branch --show-current)
        log "Detected GitHub repo: $GITHUB_REPO"
        log "Current branch: $CURRENT_BRANCH"
    else
        read -p "📂 GitHub repository (username/repo-name): " GITHUB_REPO
        CURRENT_BRANCH="main"
    fi
    
    cat > /tmp/app-spec.yaml << EOF
name: ${APP_NAME}
region: ${REGION}
services:
- name: marketing-analytics-api
  source_dir: /
  github:
    repo: ${GITHUB_REPO}
    branch: ${CURRENT_BRANCH}
    deploy_on_push: true
  dockerfile_path: Dockerfile
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-s
  routes:
  - path: /
    preserve_path_prefix: true
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 30
    timeout_seconds: 10
    success_threshold: 1
    failure_threshold: 3
  envs:
  - key: GOOGLE_CLIENT_ID
    value: "${GOOGLE_CLIENT_ID}"
    type: SECRET
    scope: RUN_TIME
  - key: GOOGLE_CLIENT_SECRET
    value: "${GOOGLE_CLIENT_SECRET}"
    type: SECRET
    scope: RUN_TIME
  - key: GOOGLE_ADS_DEVELOPER_TOKEN
    value: "${GOOGLE_ADS_DEVELOPER_TOKEN}"
    type: SECRET
    scope: RUN_TIME
  - key: GA4_PROPERTY_ID
    value: "${GA4_PROPERTY_ID:-}"
    scope: RUN_TIME
  - key: LOG_LEVEL
    value: "INFO"
    scope: RUN_TIME
  - key: PYTHONPATH
    value: "/app"
    scope: RUN_TIME
  - key: GOOGLE_REDIRECT_URI
    value: "https://${APP_NAME}.ondigitalocean.app/google-oauth/callback"
    scope: RUN_TIME
  - key: FRONTEND_URL
    value: "https://${APP_NAME}.ondigitalocean.app"
    scope: RUN_TIME
EOF
    
    log "App specification created ✅"
}

deploy_app() {
    log "Deploying to DigitalOcean App Platform..."
    
    # Check if app already exists
    if doctl apps list --format Name --no-header | grep -q "^${APP_NAME}$"; then
        warn "App ${APP_NAME} already exists. Updating..."
        APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
        doctl apps update $APP_ID --spec /tmp/app-spec.yaml
    else
        log "Creating new app..."
        doctl apps create --spec /tmp/app-spec.yaml --wait
    fi
    
    log "Deployment initiated ✅"
    
    # Wait for deployment
    log "Waiting for deployment to complete..."
    sleep 10
    
    APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
    
    # Wait for app to be running
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local status=$(doctl apps get $APP_ID --format Phase --no-header)
        if [[ "$status" == "ACTIVE" ]]; then
            log "App is running! ✅"
            break
        elif [[ "$status" == "ERROR" ]]; then
            error "Deployment failed. Check logs with: doctl apps logs $APP_ID"
        else
            log "Deployment status: $status (attempt $attempt/$max_attempts)"
            sleep 30
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        warn "Deployment taking longer than expected. Check status manually."
    fi
}

show_deployment_info() {
    local APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
    local APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header)
    
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT SUCCESSFUL! 🎉${NC}"
    echo ""
    echo -e "${BLUE}📊 Your Marketing Analytics MCP Server is live at:${NC}"
    echo "🌐 FastAPI Server: $APP_URL"
    echo "📖 API Documentation: $APP_URL/docs"
    echo "🔍 Health Check: $APP_URL/health"
    echo "🔗 OAuth Setup: $APP_URL/google-oauth/auth-url"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "1. ✅ Complete OAuth setup:"
    echo "   curl $APP_URL/google-oauth/auth-url"
    echo "   # Open the returned URL in your browser"
    echo ""
    echo "2. ✅ Update Google Console OAuth redirect URIs:"
    echo "   Add: $APP_URL/google-oauth/callback"
    echo ""
    echo "3. ✅ Configure Claude Desktop MCP:"
    cat << EOF
   {
     "mcpServers": {
       "marketing-analytics": {
         "command": "curl",
         "args": ["-s", "$APP_URL/mcp-endpoint"],
         "env": {}
       }
     }
   }
EOF
    echo ""
    echo "4. ✅ Test your deployment:"
    echo "   curl $APP_URL/health"
    echo ""
    echo -e "${BLUE}🛠️ Management Commands:${NC}"
    echo "View logs:    doctl apps logs $APP_ID --follow"
    echo "App details:  doctl apps get $APP_ID"
    echo "Update app:   doctl apps update $APP_ID --spec /tmp/app-spec.yaml"
    echo "Delete app:   doctl apps delete $APP_ID"
    echo ""
    echo -e "${GREEN}🎯 Your marketing analytics are now available globally with HTTPS! 🎯${NC}"
}

test_deployment() {
    log "Testing deployment..."
    
    local APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
    local APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header)
    
    # Test health endpoint
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s "${APP_URL}/health" >/dev/null; then
            log "Health check passed ✅"
            break
        else
            log "Waiting for app to respond (attempt $attempt/$max_attempts)..."
            sleep 15
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        warn "Health check timeout. App may still be starting up."
        echo "Check manually: curl ${APP_URL}/health"
    fi
}

cleanup() {
    rm -f /tmp/app-spec.yaml
}

# Main deployment flow
main() {
    print_banner
    
    log "🚀 Starting one-click deployment of Marketing Analytics MCP Server..."
    
    check_requirements
    collect_credentials
    create_app_spec
    deploy_app
    test_deployment
    show_deployment_info
    cleanup
    
    echo ""
    log "🎉 ONE-CLICK DEPLOYMENT COMPLETE! 🎉"
    log "Your Marketing Analytics MCP Server is now live and ready to use with Claude!"
}

# Trap to cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"