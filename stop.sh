#!/bin/bash
# EcoSphere - Stop all services
echo "🛑 Stopping EcoSphere services..."

pkill -f "server/main.py" 2>/dev/null && echo "  ✅ Server stopped" || echo "  ⚠️  Server was not running"
pkill -f "voice_pipeline.py" 2>/dev/null && echo "  ✅ Pipeline stopped" || echo "  ⚠️  Pipeline was not running"

echo ""
echo "All services stopped."
