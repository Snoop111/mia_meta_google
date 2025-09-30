#!/bin/bash
# 🚀 MIA Meta Integration - Permanent ngrok Startup Script

echo "🔗 Starting MIA with Permanent ngrok Domain: mia-analytics.ngrok.app"

# Set environment variable
export MCP_BASE_URL=https://mia-analytics.ngrok.app

# Kill any existing processes
echo "🛑 Cleaning up existing processes..."
pkill -f "uvicorn main:app"
pkill -f "ngrok http"
pkill -f "python backend/simple_adk_server.py"
sleep 2

# Start MCP Backend
echo "🚀 Starting MCP Backend (Port 8000)..."
cd mcp-backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
MCP_PID=$!
cd ..

# Start ngrok with permanent domain
echo "🌐 Starting ngrok with permanent domain..."
ngrok http 8000 --domain=mia-analytics.ngrok.app &
NGROK_PID=$!

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Start MIA Backend
echo "🚀 Starting MIA Backend (Port 8002)..."
python backend/simple_adk_server.py &
MIA_PID=$!

# Start Frontend (optional - user can run manually)
echo "📱 To start frontend, run: npm run dev"

echo ""
echo "✅ All services started!"
echo "🔗 Permanent ngrok URL: https://mia-analytics.ngrok.app"
echo "📱 Frontend: http://localhost:5173"
echo "🔧 MIA Backend: http://localhost:8002"
echo ""
echo "🛑 To stop all services: kill $MCP_PID $NGROK_PID $MIA_PID"
echo "💾 PIDs saved for cleanup: MCP=$MCP_PID NGROK=$NGROK_PID MIA=$MIA_PID"

# Keep script running
wait