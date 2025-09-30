#!/bin/bash
# Start both FastAPI and MCP Server

set -e

echo "🚀 Starting Marketing Analytics Services..."

# Install supervisor if not present
pip install supervisor

# Create log directory
mkdir -p /app/logs

# Start services with supervisor
echo "📡 Starting FastAPI server on port 8000..."
echo "🤖 Starting MCP server on port 8001..."

exec supervisord -c /app/supervisord.conf