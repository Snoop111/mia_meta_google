#!/bin/bash
# 🚀 Simple Deploy Script for Marketing Analytics MCP Server
# Uses Docker build with DigitalOcean App Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_NAME="marketing-analytics-mcp"

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║               🚀 SIMPLE DEPLOY SCRIPT 🚀                    ║
║                                                              ║
║  Deploys Marketing Analytics MCP Server to DigitalOcean     ║
║  Uses Docker for reliable deployment                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

check_requirements() {
    log "Checking requirements..."
    
    # Check doctl CLI
    if ! command -v doctl &> /dev/null; then
        error "Please install doctl CLI first: brew install doctl"
    fi
    
    # Check if logged in
    if ! doctl account get >/dev/null 2>&1; then
        warn "Not logged in to DigitalOcean. Please authenticate:"
        doctl auth init
    fi
    
    # Check git repository
    if ! git remote -v >/dev/null 2>&1; then
        error "This directory is not a git repository. Please initialize git and push to GitHub first."
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

create_simple_app_spec() {
    log "Creating simple app specification..."
    
    # Get GitHub repo and branch info
    GITHUB_REPO=$(git remote get-url origin | sed 's/.*github.com[\/:]//; s/\.git$//')
    CURRENT_BRANCH=$(git branch --show-current)
    
    log "GitHub repo: $GITHUB_REPO"
    log "Branch: $CURRENT_BRANCH"
    
    cat > /tmp/app-spec.yaml << EOF
name: ${APP_NAME}
region: nyc1
services:
- name: marketing-analytics
  source_dir: /
  github:
    repo: ${GITHUB_REPO}
    branch: ${CURRENT_BRANCH}
    deploy_on_push: true
  dockerfile_path: Dockerfile.dual-service
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-s
  routes:
  - path: /
    preserve_path_prefix: true
  health_check:
    http_path: /health
    initial_delay_seconds: 120
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
  - key: PORT
    value: "8080"
    scope: RUN_TIME
EOF
    
    log "App specification created ✅"
}

create_dual_service_dockerfile() {
    log "Creating dual-service Dockerfile..."
    
    if [[ ! -f "Dockerfile.dual-service" ]]; then
        cat > Dockerfile.dual-service << 'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-mcp.txt requirements-data-apis.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-mcp.txt && \
    pip install --no-cache-dir -r requirements-data-apis.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs /var/log/supervisor && \
    chmod 755 /app/data /app/logs

# Create supervisor config
RUN cat > /etc/supervisor/conf.d/supervisord.conf << 'SEOF'
[supervisord]
nodaemon=true
user=root

[program:fastapi]
command=uvicorn main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/fastapi.out.log
stderr_logfile=/var/log/supervisor/fastapi.err.log

[program:healthcheck]
command=python -m http.server 8080
directory=/app
autostart=true  
autorestart=true
stdout_logfile=/var/log/supervisor/health.out.log
stderr_logfile=/var/log/supervisor/health.err.log
SEOF

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
EOF
        log "Created Dockerfile.dual-service ✅"
    else
        log "Dockerfile.dual-service already exists ✅"
    fi
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
}

show_deployment_info() {
    local APP_ID=$(doctl apps list --format ID,Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
    local APP_URL=$(doctl apps get $APP_ID --format LiveURL --no-header 2>/dev/null || echo "https://${APP_NAME}.ondigitalocean.app")
    
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT INITIATED! 🎉${NC}"
    echo ""
    echo -e "${BLUE}📊 Your app will be available at:${NC}"
    echo "🌐 App URL: $APP_URL"
    echo "📖 Health Check: $APP_URL/health"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "1. ✅ Wait for deployment to complete (5-10 minutes)"
    echo "2. ✅ Check deployment status:"
    echo "   doctl apps get $APP_ID"
    echo ""
    echo "3. ✅ View deployment logs:"
    echo "   doctl apps logs $APP_ID --follow"
    echo ""
    echo "4. ✅ Once live, complete OAuth setup:"
    echo "   curl $APP_URL/google-oauth/auth-url"
    echo ""
    echo -e "${BLUE}🛠️ Management Commands:${NC}"
    echo "View logs:    doctl apps logs $APP_ID --follow"
    echo "App details:  doctl apps get $APP_ID"
    echo "Delete app:   doctl apps delete $APP_ID"
}

cleanup() {
    rm -f /tmp/app-spec.yaml
}

# Main deployment flow
main() {
    print_banner
    
    log "🚀 Starting simple deployment of Marketing Analytics MCP Server..."
    
    check_requirements
    collect_credentials
    create_dual_service_dockerfile
    create_simple_app_spec
    deploy_app
    show_deployment_info
    cleanup
    
    echo ""
    log "🎉 DEPLOYMENT INITIATED! 🎉"
    log "Check status with: doctl apps list"
}

# Trap to cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"