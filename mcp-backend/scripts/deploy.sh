#!/bin/bash
# Marketing Analytics MCP Server Deployment Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="marketing-analytics-mcp"
CONTAINER_NAME="marketing-analytics"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_requirements() {
    log "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check .env file
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        warn ".env file not found. Creating from template..."
        cp "$PROJECT_DIR/.env.docker.example" "$PROJECT_DIR/.env"
        warn "Please edit .env file with your actual API credentials before continuing."
        exit 1
    fi
    
    log "Requirements check passed ✅"
}

build_image() {
    log "Building Docker image..."
    cd "$PROJECT_DIR"
    
    docker build -t "$IMAGE_NAME:latest" .
    
    if [[ $? -eq 0 ]]; then
        log "Docker image built successfully ✅"
    else
        error "Failed to build Docker image"
    fi
}

start_services() {
    log "Starting services with Docker Compose..."
    cd "$PROJECT_DIR"
    
    # Start basic services
    docker-compose up -d
    
    if [[ $? -eq 0 ]]; then
        log "Services started successfully ✅"
    else
        error "Failed to start services"
    fi
}

run_health_checks() {
    log "Running health checks..."
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Check container status
    if docker-compose ps | grep -q "Up"; then
        log "Containers are running ✅"
    else
        error "Some containers are not running properly"
    fi
    
    # Check FastAPI server
    local max_attempts=10
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:8000/docs > /dev/null; then
            log "FastAPI server is responding ✅"
            break
        else
            log "Attempt $attempt/$max_attempts: Waiting for FastAPI server..."
            sleep 5
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "FastAPI server health check failed"
    fi
    
    # Test MCP server
    log "Testing MCP server..."
    docker-compose exec -T marketing-analytics python test_mcp_server.py
    
    if [[ $? -eq 0 ]]; then
        log "MCP server test passed ✅"
    else
        warn "MCP server test failed - this might be due to missing OAuth setup"
    fi
}

show_status() {
    log "Deployment Status:"
    echo ""
    
    # Container status
    echo -e "${BLUE}Container Status:${NC}"
    docker-compose ps
    echo ""
    
    # Service URLs
    echo -e "${BLUE}Service URLs:${NC}"
    echo "FastAPI Server: http://localhost:8000"
    echo "FastAPI Docs:   http://localhost:8000/docs"
    echo "MCP Server:     http://localhost:8001"
    echo ""
    
    # Logs
    echo -e "${BLUE}View Logs:${NC}"
    echo "docker-compose logs -f marketing-analytics"
    echo ""
    
    # OAuth setup
    echo -e "${BLUE}OAuth Setup:${NC}"
    echo "python verify_oauth_setup.py"
    echo ""
    
    # Claude Desktop config
    echo -e "${BLUE}Claude Desktop Configuration:${NC}"
    echo "Update your Claude Desktop config with:"
    echo "$(cat "$PROJECT_DIR/claude_desktop_venv_config.json" | head -10)..."
}

cleanup() {
    log "Stopping services..."
    cd "$PROJECT_DIR"
    docker-compose down
    
    if [[ "$1" == "--remove-data" ]]; then
        warn "Removing data volumes..."
        docker-compose down -v
        rm -rf data/ logs/
    fi
}

# Main deployment function
deploy() {
    log "🚀 Starting Marketing Analytics MCP Server deployment..."
    
    check_requirements
    build_image
    start_services
    run_health_checks
    show_status
    
    log "🎉 Deployment completed successfully!"
    log ""
    log "Next steps:"
    log "1. Complete OAuth setup: python verify_oauth_setup.py"
    log "2. Configure Claude Desktop with the provided configuration"
    log "3. Start using your marketing analytics with Claude!"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTION]"
    echo "Deploy Marketing Analytics MCP Server"
    echo ""
    echo "Options:"
    echo "  deploy              Deploy the application (default)"
    echo "  build               Build Docker image only"
    echo "  start               Start services only"
    echo "  stop                Stop services"
    echo "  restart             Restart services"
    echo "  status              Show deployment status"
    echo "  logs                Show service logs"
    echo "  cleanup             Stop and cleanup"
    echo "  cleanup --remove-data    Stop, cleanup, and remove data"
    echo "  --help              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 deploy           # Full deployment"
    echo "  $0 build            # Build image only"
    echo "  $0 logs             # View logs"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build")
        check_requirements
        build_image
        ;;
    "start")
        check_requirements
        start_services
        ;;
    "stop")
        cleanup
        ;;
    "restart")
        cleanup
        sleep 5
        start_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        cd "$PROJECT_DIR"
        docker-compose logs -f
        ;;
    "cleanup")
        cleanup "$2"
        ;;
    "--help"|"help")
        usage
        ;;
    *)
        error "Unknown option: $1. Use --help for usage information."
        ;;
esac