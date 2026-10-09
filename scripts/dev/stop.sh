#!/usr/bin/env bash
# 开发模式停止
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "==> 停止前后端 ..."
[ -f /tmp/csp_backend.pid ] && kill "$(cat /tmp/csp_backend.pid)" 2>/dev/null && rm -f /tmp/csp_backend.pid
[ -f /tmp/csp_frontend.pid ] && kill "$(cat /tmp/csp_frontend.pid)" 2>/dev/null && rm -f /tmp/csp_frontend.pid
# 兜底清理
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
echo "==> 已停止。"
