#!/usr/bin/env bash
# 开发模式启动：后端(uvicorn 热重载) + 前端(vite 热重载)
# 前端通过 vite proxy 将 /api 转发到后端 8080。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==> 启动后端 (http://127.0.0.1:8080) ..."
cd "$ROOT/backend"
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload > /tmp/csp_backend.log 2>&1 &
echo $! > /tmp/csp_backend.pid

echo "==> 启动前端 (http://127.0.0.1:5173) ..."
cd "$ROOT/frontend"
npm run dev > /tmp/csp_frontend.log 2>&1 &
echo $! > /tmp/csp_frontend.pid

echo "==> 开发环境就绪：浏览器打开 http://127.0.0.1:5173"
