#!/bin/bash

# Quick test script to verify the FastAPI application and every feature is working
echo "🧪 Testing FastAPI Boilerplate v3..."

BASE=http://localhost:8000
EMAIL="quick_$(date +%s)@example.com"
PASSWORD="quickpassword123"

# Start the server in background
echo "Starting server..."
# setsid puts the server (uv + uvicorn reloader) in its own process group
setsid ./run.sh > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
for _ in $(seq 1 30); do
    curl -s $BASE/api/health/ > /dev/null && break
    sleep 1
done

check() {
    if eval "$2"; then echo "✅ $1"; else echo "❌ $1"; fi
}

# Health / pages
check "Health check" "curl -s $BASE/api/health/ | grep -q healthy"
check "Main page loaded" "curl -s $BASE/ | grep -q 'FastAPI Boilerplate v3'"
check "API docs accessible" "curl -s $BASE/docs | grep -q swagger"

# FastAPI Users
check "Register" "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE/api/auth/register \
    -H 'Content-Type: application/json' -d '{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}' | grep -q 201"
TOKEN=$(curl -s -X POST $BASE/api/auth/jwt/login -d "username=$EMAIL&password=$PASSWORD" \
    | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
check "Login (JWT issued)" "[ -n '$TOKEN' ]"
check "Current user" "curl -s $BASE/api/users/me -H 'Authorization: Bearer $TOKEN' | grep -q '$EMAIL'"

# CrudRouter
check "Create item (auth)" "curl -s -X POST $BASE/api/items -H 'Authorization: Bearer $TOKEN' \
    -H 'Content-Type: application/json' -d '{\"name\":\"quick\",\"price\":1}' | grep -q quick"
check "List items" "curl -s $BASE/api/items | grep -q quick"

# Cache
curl -s -o /dev/null $BASE/api/demo/cached
check "Cache HIT" "curl -s -D - -o /dev/null $BASE/api/demo/cached | grep -qi 'x-fastapi-cache: HIT'"

# Limiter (5 req / 60s)
for _ in $(seq 1 5); do curl -s -o /dev/null $BASE/api/demo/limited; done
check "Rate limit (429)" "curl -s -o /dev/null -w '%{http_code}' $BASE/api/demo/limited | grep -q 429"

# Clean up
echo "Stopping server..."
kill -- -$SERVER_PID 2>/dev/null || kill $SERVER_PID
rm -f server.log

echo "✅ All tests completed!"
