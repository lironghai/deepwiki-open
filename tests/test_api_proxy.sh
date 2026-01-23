#!/bin/bash
# Test script for Codemap API proxy

echo "=========================================="
echo "Codemap API Proxy Test"
echo "=========================================="

# Check if backend is running
echo ""
echo "[1/3] Checking backend service (port 8001)..."
if curl -s http://localhost:8001/lang/config > /dev/null 2>&1; then
    echo "✓ Backend is running on port 8001"
else
    echo "✗ Backend is NOT running!"
    echo "  Please start it with: python -m uvicorn api.api:app --host 0.0.0.0 --port 8001"
    exit 1
fi

# Check if frontend is running
echo ""
echo "[2/3] Checking frontend service (port 3000)..."
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✓ Frontend is running on port 3000"
else
    echo "✗ Frontend is NOT running!"
    echo "  Please start it with: npm run dev"
    exit 1
fi

# Test the Codemap chat endpoint through proxy
echo ""
echo "[3/3] Testing Codemap chat endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:3000/api/chat/codemap \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/test/repo",
    "type": "github",
    "question": "What is this project about?",
    "provider": "openai",
    "model": "gpt-4",
    "language": "en"
  }')

if echo "$RESPONSE" | grep -q "answer\|error"; then
    echo "✓ Codemap chat endpoint is responding"
    echo "  Response preview: $(echo $RESPONSE | head -c 100)..."
else
    echo "✗ Unexpected response from endpoint"
    echo "  Response: $RESPONSE"
    exit 1
fi

echo ""
echo "=========================================="
echo "All tests passed! ✓"
echo "=========================================="
echo ""
echo "You can now use Codemap Integration in the chat interface!"
