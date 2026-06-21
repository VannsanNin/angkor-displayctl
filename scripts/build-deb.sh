#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "==> Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info debian/.debhelper debian/displayctl/ debian/files 2>/dev/null || true

echo "==> Building Debian package..."
dpkg-buildpackage -b -us -uc

echo "==> Moving .deb to scripts/ directory..."
mkdir -p "$PROJECT_DIR/scripts"
mv ../displayctl_*.deb "$PROJECT_DIR/scripts/" 2>/dev/null || true

echo "==> Done! Package built in scripts/ directory."
ls -lh "$PROJECT_DIR"/scripts/displayctl_*.deb 2>/dev/null || echo "(not found, check parent directory)"
