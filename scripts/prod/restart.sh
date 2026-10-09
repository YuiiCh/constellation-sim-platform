#!/usr/bin/env bash
# 生产模式重启
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$ROOT/scripts/prod/stop.sh"
sleep 1
bash "$ROOT/scripts/prod/start.sh"
