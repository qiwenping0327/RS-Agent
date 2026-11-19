#!/bin/bash
echo "=============================================="
echo "  RS-Agent 服务停止脚本"
echo "=============================================="
echo ""

echo "[1/4] 停止 Vite 前端服务器..."
PID=$(lsof -ti :5173)
if [ -n "${PID}" ]; then
    kill -9 "${PID}" 2>/dev/null || true
    echo "  已停止 (PID: ${PID})"
else
    echo "  未运行"
fi

echo ""
echo "[2/4] 停止 Express 服务器..."
PID=$(lsof -ti :3001)
if [ -n "${PID}" ]; then
    kill -9 "${PID}" 2>/dev/null || true
    echo "  已停止 (PID: ${PID})"
else
    echo "  未运行"
fi

echo ""
echo "[3/4] 停止 Gateway 服务..."
PID=$(lsof -ti :18789)
if [ -n "${PID}" ]; then
    kill -9 "${PID}" 2>/dev/null || true
    echo "  已停止 (PID: ${PID})"
else
    echo "  未运行"
fi

echo ""
echo "[4/4] 停止 Python OEA 服务..."
PID=$(lsof -ti :8765)
if [ -n "${PID}" ]; then
    kill -9 "${PID}" 2>/dev/null || true
    echo "  已停止 (PID: ${PID})"
else
    echo "  未运行"
fi

echo ""
echo "=============================================="
echo "  服务停止完成！"
echo "=============================================="
