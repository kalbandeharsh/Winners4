#!/bin/bash
# EcoSphere - One-click startup script
echo "🚀 Starting EcoSphere Voice AI Sales Agent..."
echo ""

# Kill any existing processes
pkill -f "server/main.py" 2>/dev/null
pkill -f "voice_pipeline.py" 2>/dev/null
sleep 1

# Start the FastAPI server in background
echo "📡 Starting FastAPI server on port 8000..."
python3 server/main.py &
SERVER_PID=$!
sleep 3

# Check if server started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is running (PID: $SERVER_PID)"
else
    echo "❌ Server failed to start. Check for errors above."
    exit 1
fi

# Start the voice pipeline
echo "🎙️ Starting voice pipeline..."
python3 voice_pipeline.py &
PIPELINE_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "✅ EcoSphere is running!"
echo "=========================================="
echo ""
echo "📋 Next steps:"
echo "   1. Copy the CHANNEL NAME from above"
echo "   2. Open demo.html in your browser"
echo "   3. Paste the channel name and click Join"
echo ""
echo "🔧 To stop: ./stop.sh"
echo "   Or press Ctrl+C"
echo ""

# Wait for either process to exit
wait
