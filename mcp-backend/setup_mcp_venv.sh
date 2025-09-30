#!/bin/bash
# Setup Marketing Analytics MCP Server in virtual environment

echo "🚀 Setting up Marketing Analytics MCP Server..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install MCP library
echo "📥 Installing MCP library..."
pip install mcp

# Install other requirements
echo "📥 Installing project requirements..."
pip install -r requirements-mcp.txt

# Install project in development mode
echo "🔨 Installing project in development mode..."
pip install -e .

echo "✅ Setup complete!"
echo ""
echo "To use the MCP server:"
echo "1. Activate your venv: source venv/bin/activate"
echo "2. Test the server: python test_mcp_server.py"
echo "3. Check environment: python start_mcp_server.py --check-env"
echo "4. Start server: python start_mcp_server.py"
echo ""
echo "For Claude Desktop integration, update the config with your venv python:"
echo "$(pwd)/venv/bin/python"