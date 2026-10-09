#!/usr/bin/env bash
# 生产/本地部署模式：单端口（后端同时托管前端构建产物）
# 后端在 8080 提供 API 与静态页面，外部可通过该端口访问。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==> 构建前端 ..."
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run build

echo "==> 启动后端 (单端口 http://0.0.0.0:8080) ..."
cd "$ROOT/backend"
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 > /tmp/csp_prod.log 2>&1 &
echo $! > /tmp/csp_prod.pid
echo "==> 部署就绪：监听 0.0.0.0:8080"
