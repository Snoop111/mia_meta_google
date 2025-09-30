#!/usr/bin/env python3
"""
Marketing Analytics MCP Server Launcher

This script provides a convenient way to start the MCP server with proper
environment setup and configuration validation.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_environment() -> Dict[str, bool]:
    """Check required and optional environment variables"""
    
    # Load configuration
    config_path = Path(__file__).parent / "mcp_config.json"
    if not config_path.exists():
        logger.error("MCP configuration file not found: mcp_config.json")
        sys.exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    env_config = config.get("environment", {})
    required_vars = env_config.get("required_vars", [])
    optional_vars = env_config.get("optional_vars", [])
    
    results = {}
    missing_required = []
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        results[var] = bool(value)
        if not value:
            missing_required.append(var)
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        results[var] = bool(value)
    
    # Report status
    logger.info("Environment variable check:")
    for var, present in results.items():
        status = "✅" if present else ("❌" if var in required_vars else "⚠️")
        logger.info(f"  {status} {var}: {'Present' if present else 'Not set'}")
    
    if missing_required:
        logger.error(f"Missing required environment variables: {missing_required}")
        logger.error("Please set these variables before starting the server")
        return results
    
    logger.info("✅ Environment check passed")
    return results

def setup_database():
    """Initialize database if needed"""
    try:
        from database import credential_storage
        credential_storage._init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

def validate_imports():
    """Validate that all required modules can be imported"""
    try:
        # Test core imports
        import mcp
        import pandas
        import google.auth
        logger.info("✅ Core dependencies imported successfully")
        
        # Test our modules
        from routes.comprehensive_insights import comprehensive_insights
        from analytics.ad_performance import AdPerformanceAnalyzer
        from credential_manager import credential_manager
        logger.info("✅ Analytics modules imported successfully")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Please install required dependencies: pip install -e .")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Module validation failed: {e}")
        sys.exit(1)

def print_startup_banner():
    """Print startup banner with server info"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                Marketing Analytics MCP Server                ║
║                                                              ║
║  🎯 Multi-platform marketing analytics                      ║
║  📊 Google Ads, GA4, Meta Ads support                      ║
║  🔄 Cross-platform insights and optimization               ║
║  🛠️ MCP-compatible tools and prompts                        ║
║                                                              ║
║  Ready to analyze your marketing data!                       ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

async def start_server(host: str = "localhost", port: Optional[int] = None):
    """Start the MCP server with proper setup"""
    
    logger.info("🚀 Starting Marketing Analytics MCP Server...")
    
    # Pre-flight checks
    print_startup_banner()
    
    logger.info("Step 1/4: Checking environment...")
    env_status = check_environment()
    
    logger.info("Step 2/4: Validating imports...")
    validate_imports()
    
    logger.info("Step 3/4: Setting up database...")
    setup_database()
    
    logger.info("Step 4/4: Starting MCP server...")
    
    try:
        # Import and start the MCP server
        from mcp_server import main
        await main()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise

def print_usage():
    """Print usage information"""
    usage = """
Usage: python3 start_mcp_server.py [options]

Options:
  -h, --help              Show this help message
  --check-env             Check environment variables only
  --validate-imports      Validate imports only
  --setup-db              Setup database only
  --host HOST             Server host (default: localhost)
  --port PORT             Server port (optional)

Environment Variables:
  Required:
    GOOGLE_CLIENT_ID           Google OAuth client ID
    GOOGLE_CLIENT_SECRET       Google OAuth client secret
    GOOGLE_ADS_DEVELOPER_TOKEN Google Ads developer token

  Optional:
    GA4_PROPERTY_ID           GA4 property ID
    META_APP_ID               Meta app ID
    META_APP_SECRET           Meta app secret
    GOOGLE_APPLICATION_CREDENTIALS  Service account file path

Examples:
  python3 start_mcp_server.py
  python3 start_mcp_server.py --check-env
  python3 start_mcp_server.py --host 0.0.0.0 --port 8080
"""
    print(usage)

def main():
    """Main entry point"""
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print_usage()
        return
    
    if "--check-env" in args:
        check_environment()
        return
        
    if "--validate-imports" in args:
        validate_imports()
        return
        
    if "--setup-db" in args:
        setup_database()
        return
    
    # Parse host/port
    host = "localhost"
    port = None
    
    if "--host" in args:
        host_idx = args.index("--host")
        if host_idx + 1 < len(args):
            host = args[host_idx + 1]
    
    if "--port" in args:
        port_idx = args.index("--port")
        if port_idx + 1 < len(args):
            try:
                port = int(args[port_idx + 1])
            except ValueError:
                logger.error("Invalid port number")
                sys.exit(1)
    
    # Start the server
    try:
        asyncio.run(start_server(host, port))
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()