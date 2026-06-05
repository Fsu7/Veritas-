#!/usr/bin/env bash
# Task27 启动测试用 Python AI 服务
# 注入 USE_MOCK_LLM=1 + USE_MOCK_CHROMA=1 环境变量
# 输出 PID 到 .test_server.pid
# 等待服务就绪（curl /health 检查）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="$PROJECT_DIR/.test_server.pid"
HOST="127.0.0.1"
PORT=8199
MAX_WAIT=30

# 如果已有进程在运行，先停止
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing test server (PID=$OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

cd "$PROJECT_DIR"

echo "Starting test AI service on ${HOST}:${PORT}..."
echo "  USE_MOCK_LLM=1"
echo "  USE_MOCK_CHROMA=1"

USE_MOCK_LLM=1 \
USE_MOCK_CHROMA=1 \
python3 -m uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    &

SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "Server PID: $SERVER_PID"

# 等待服务就绪
echo "Waiting for service to be ready (max ${MAX_WAIT}s)..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "ERROR: Server process exited unexpectedly."
        rm -f "$PID_FILE"
        exit 1
    fi

    if curl -sf "http://${HOST}:${PORT}/health" > /dev/null 2>&1; then
        echo "Service is ready! (took ${ELAPSED}s)"
        echo "  Health check: http://${HOST}:${PORT}/health"
        echo "  API base:     http://${HOST}:${PORT}/api"
        echo "  PID file:     $PID_FILE"
        exit 0
    fi

    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "ERROR: Service did not become ready within ${MAX_WAIT}s."
kill "$SERVER_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
