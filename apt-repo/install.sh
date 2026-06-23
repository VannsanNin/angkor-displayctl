#!/bin/bash
set -euo pipefail

REPO_BASE="https://vannsannin.github.io/angkor-displayctl"
KEYRING="/usr/share/keyrings/displayctl.gpg"
SOURCES="/etc/apt/sources.list.d/displayctl.list"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Use: curl -fsSL $REPO_BASE/install.sh | sudo bash"
    exit 1
fi

echo "==> Adding displayctl GPG key..."
curl -fsSL "$REPO_BASE/gpg.key" | gpg --dearmor -o "$KEYRING"

echo "==> Adding displayctl APT repository..."
echo "deb [signed-by=$KEYRING] $REPO_BASE jammy main" > "$SOURCES"

echo "==> Updating package lists..."
apt update

echo "==> Installing displayctl..."
apt install -y displayctl

echo "==> Done! Run 'displayctl --help' to get started."
