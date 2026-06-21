#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")/apt-repo"
DEB_FILE="${1:-}"

if [ -z "$DEB_FILE" ] || [ ! -f "$DEB_FILE" ]; then
    echo "Usage: $0 <path-to-deb-file>"
    echo "Adds a .deb package to the APT repository for all configured codenames."
    exit 1
fi

if ! command -v reprepro >/dev/null 2>&1; then
    echo "Error: reprepro is not installed. Install it with: sudo apt install reprepro"
    exit 1
fi

cd "$REPO_DIR"
CODENAMES=$(grep '^Codename:' conf/distributions | awk '{print $2}')

for codename in $CODENAMES; do
    echo "==> Adding $DEB_FILE to $codename..."
    reprepro --component main includedeb "$codename" "$DEB_FILE"
done

echo "==> Done."
