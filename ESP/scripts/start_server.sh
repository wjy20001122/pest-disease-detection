#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8010
