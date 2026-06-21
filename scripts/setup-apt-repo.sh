#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$PROJECT_DIR/apt-repo"
CONF_DIR="$REPO_DIR/conf"
POOL_DIR="$REPO_DIR/pool/main"
DISTS_DIR="$REPO_DIR/dists"

CODENAMES=("jammy" "focal" "noble")
COMPONENT="main"

echo "==> Setting up APT repository structure..."

mkdir -p "$CONF_DIR" "$POOL_DIR"

# Create distributions config
cat > "$CONF_DIR/distributions" << 'DISTEOF'
Codename: jammy
Suite: stable
Components: main
Architectures: all source
SignWith: yes
Description: displayctl APT repository for Ubuntu jammy

DISTEOF

for codename in "${CODENAMES[@]:1}"; do
    cat >> "$CONF_DIR/distributions" << DISTEOF

Codename: $codename
Suite: stable
Components: main
Architectures: all source
SignWith: yes
Description: displayctl APT repository for Ubuntu $codename

DISTEOF
done

# Build the .deb if not already present
DEB_FILE="$PROJECT_DIR/scripts/displayctl_1.0.0-1_all.deb"
if [ ! -f "$DEB_FILE" ]; then
    echo "==> Building .deb package first..."
    cd "$PROJECT_DIR"
    dpkg-buildpackage -b -us -uc
    mkdir -p "$PROJECT_DIR/scripts"
    mv ../displayctl_*.deb "$DEB_FILE" 2>/dev/null || true
fi

# Add .deb to repository
if [ -f "$DEB_FILE" ]; then
    echo "==> Adding package to repository..."
    for codename in "${CODENAMES[@]}"; do
        reprepro -b "$REPO_DIR" --component "$COMPONENT" includedeb "$codename" "$DEB_FILE"
    done
else
    echo "==> No .deb found; copy packages to $POOL_DIR manually."
fi

echo "==> APT repository ready at $REPO_DIR"
echo "    Serve with: cd $REPO_DIR && python3 -m http.server 8080"
