#!/bin/bash
set -e

echo "=============================================="
echo "  RS-Agent 服务启动脚本"
echo "=============================================="
echo ""

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(dirname "${SCRIPT_DIR}")
DEPLOY_DIR="/opt/rs-agent"
DATA_DIR="/data/rs-agent"
LOG_DIR="/var/log/rs-agent"

NODE_VERSION="22.12.0"
NODE_BIN="/opt/node-v${NODE_VERSION}-linux-x64/bin"
export PATH="${NODE_BIN}:${PATH}"

echo "[1/4] 启动 Python OpenEarthEngine 服务..."
if lsof -i :8765 > /dev/null 2>&1; then
    echo "  端口 8765 已被占用，跳过"
else
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate rs-agent
    
    export VOLCENGINE_URL="https://ark.cn-beijing.volces.com/api/v3"
    export VOLCENGINE_API_KEY="${VOLCENGINE_API_KEY:-}"
    export VOLCENGINE_MODEL="doubao-seed-1-8-251228"
    export VOLCENGINE_PROVIDER="volcengine"
    
    cd "${PROJECT_DIR}/open-earth-engine"
    nohup python oea_service.py > "${LOG_DIR}/oea-service.log" 2>&1 &
    echo "  已启动 (PID: $!)"
    
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/open-earth/knowledge/stats | grep -q "200"; then
        echo "  ✅ OEA 服务就绪"
    else
        echo "  ⚠️  OEA 服务启动中..."
    fi
fi

echo ""
echo "[2/4] 启动 RsAgent Gateway 服务..."
if lsof -i :18789 > /dev/null 2>&1; then
    echo "  端口 18789 已被占用，跳过"
else
    cd "${PROJECT_DIR}"
    nohup node dist/src/cli/pilotdeck.js server > "${LOG_DIR}/gateway.log" 2>&1 &
    echo "  已启动 (PID: $!)"
    
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:18789 | grep -q "404"; then
        echo "  ✅ Gateway 服务就绪"
    else
        echo "  ⚠️  Gateway 服务启动中..."
    fi
fi

echo ""
echo "[3/4] 启动 Express 服务器..."
if lsof -i :3001 > /dev/null 2>&1; then
    echo "  端口 3001 已被占用，跳过"
else
    cd "${PROJECT_DIR}/ui"
    nohup node --experimental-sqlite server/index.js > "${LOG_DIR}/express.log" 2>&1 &
    echo "  已启动 (PID: $!)"
    
    sleep 5
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "302"; then
        echo "  ✅ Express 服务器就绪"
    else
        echo "  ⚠️  Express 服务器启动中..."
    fi
fi

echo ""
echo "[4/4] 启动 Vite 前端服务器..."
if lsof -i :5173 > /dev/null 2>&1; then
    echo "  端口 5173 已被占用，跳过"
else
    cd "${PROJECT_DIR}/ui"
    nohup npx vite --host 0.0.0.0 > "${LOG_DIR}/vite.log" 2>&1 &
    echo "  已启动 (PID: $!)"
    
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 | grep -q "200"; then
        echo "  ✅ Vite 前端就绪"
    else
        echo "  ⚠️  Vite 前端启动中..."
    fi
fi

echo ""
echo "=============================================="
echo "  服务启动完成！"
echo "=============================================="
echo ""
echo "服务状态:"
echo "  Gateway:       http://localhost:18789"
echo "  Express:       http://localhost:3001"
echo "  Python OEA:    http://localhost:8765"
echo "  Vite 前端:     http://localhost:5173"
echo ""
echo "访问地址: http://localhost:5173"
echo ""
echo "日志目录: ${LOG_DIR}"
