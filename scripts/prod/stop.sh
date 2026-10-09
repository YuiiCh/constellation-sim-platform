#!/usr/bin/env bash
# 生产模式停止
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "==> 停止生产服务 ..."
[ -f /tmp/csp_prod.pid ] && kill "$(cat /tmp/csp_prod.pid)" 2>/dev/null && rm -f /tmp/csp_prod.pid
pkill -f "uvicorn app.main:app" 2>/dev/null || true
echo "==> 已停止。"
