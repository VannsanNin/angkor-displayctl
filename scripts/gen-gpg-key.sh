#!/bin/bash
set -euo pipefail

KEY_NAME="displayctl Repository Signing Key"
KEY_EMAIL="maintainer@displayctl.dev"
KEY_FILE="${HOME}/.gnupg/displayctl-key.asc"
PUB_KEY_FILE="apt-repo/gpg.key"

echo "==> Generating GPG signing key (non-interactive)..."

if gpg --list-keys "$KEY_EMAIL" >/dev/null 2>&1; then
    echo "=> Key for $KEY_EMAIL already exists."
else
    cat > /tmp/gpg-batch << GPGEOF
%no-protection
%transient-key
Key-Type: eddsa
Key-Curve: ed25519
Key-Usage: sign
Name-Real: $KEY_NAME
Name-Email: $KEY_EMAIL
Expire-Date: 0
%commit
GPGEOF
    gpg --batch --generate-key /tmp/gpg-batch
    rm -f /tmp/gpg-batch
    echo "=> Key generated."
fi

echo "==> Exporting public key to $PUB_KEY_FILE..."
mkdir -p "$(dirname "$PUB_KEY_FILE")"
gpg --armor --export "$KEY_EMAIL" > "$PUB_KEY_FILE"
echo "==> Done. Public key: $PUB_KEY_FILE"
echo "    Import with: sudo gpg --dearmor -o /usr/share/keyrings/displayctl.gpg < $PUB_KEY_FILE"
