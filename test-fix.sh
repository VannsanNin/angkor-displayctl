#!/bin/bash
SNAP=/snap/displayctl/5
mkdir -p /tmp/displayctl-fix
cat > /tmp/displayctl-fix/sitecustomize.py << 'EOF'
import sys, os
snap = os.environ.get("SNAP", "")
if snap:
    dynload = os.path.join(snap, "gnome-platform", "usr", "lib", "python3.12", "lib-dynload")
    if os.path.isdir(dynload) and dynload not in sys.path:
        sys.path.append(dynload)
EOF
PYTHONPATH=/tmp/displayctl-fix exec snap run displayctl "$@"
