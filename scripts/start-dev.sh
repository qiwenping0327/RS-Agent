#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

NODE_CANDIDATES=(
    "$HOME/.workbuddy/binaries/node/versions/22.12.0/bin/node"
    "$HOME/.workbuddy/binaries/node/versions/20.18.0/bin/node"
    "$HOME/.trae-cn-server/bin/stable-2a1926816d08d71538a3de294bf301b26ac911e0-debian10/node"
    "$HOME/.codebuddy-server-cn/bin/3edf87df753e170de36ac84b22b49add86afd0b4/node"
    "/usr/bin/node"
    "/usr/local/bin/node"
)

NPM_CANDIDATES=(
    "$HOME/.workbuddy/binaries/node/versions/22.12.0/bin/npm"
    "$HOME/.workbuddy/binaries/node/versions/20.18.0/bin/npm"
    "/usr/bin/npm"
    "/usr/local/bin/npm"
)

NODE_BIN=""
for candidate in "${NODE_CANDIDATES[@]}"; do
    if [ -x "$candidate" ]; then
        NODE_BIN="$candidate"
        NODE_DIR="$(dirname "$NODE_BIN")"
        break
    fi
done

if [ -z "$NODE_BIN" ]; then
    echo "[ERROR] Could not find Node.js executable"
    echo "Please install Node.js or check the candidates in the script"
    exit 1
fi

echo "[INFO] Found Node.js at: $NODE_BIN"
echo "[INFO] Node version: $($NODE_BIN --version)"

export PATH="$NODE_DIR:$PATH"

echo ""
echo "=========================================="
echo "  RsAgent Dev Environment"
echo "=========================================="
echo "Repo: $REPO_ROOT"
echo ""

cd "$REPO_ROOT"

echo "[INFO] Starting Python OpenEarthEngine service (port 8765)..."
cd "$REPO_ROOT/open-earth-engine"
python3 oea_service.py &
OEA_PID=$!
sleep 2
echo "[INFO] Python OEA service started (PID: $OEA_PID)"

echo ""
echo "[INFO] Starting dev-launcher..."
cd "$REPO_ROOT"
"$NODE_BIN" scripts/dev-launcher.mjs
