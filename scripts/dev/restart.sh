#!/usr/bin/env bash
# 开发模式重启
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$ROOT/scripts/dev/stop.sh"
sleep 1
bash "$ROOT/scripts/dev/start.sh"
