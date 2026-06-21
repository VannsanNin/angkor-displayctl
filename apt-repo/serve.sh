#!/bin/bash
set -euo pipefail
PORT="${1:-8080}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "==> Serving APT repository on http://0.0.0.0:${PORT}/"
cd "$SCRIPT_DIR"
exec python3 -m http.server "$PORT"
