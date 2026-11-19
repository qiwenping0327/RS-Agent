#!/bin/bash
echo "=============================================="
echo "  RS-Agent 服务状态检查"
echo "=============================================="
echo ""

echo "服务状态:"
echo ""

echo "[Gateway] 端口 18789:"
PID=$(lsof -ti :18789)
if [ -n "${PID}" ]; then
    echo "  ✅ 运行中 (PID: ${PID})"
    curl -s -o /dev/null -w "  HTTP状态: %{http_code}\n" http://localhost:18789
else
    echo "  ❌ 未运行"
fi

echo ""
echo "[Express] 端口 3001:"
PID=$(lsof -ti :3001)
if [ -n "${PID}" ]; then
    echo "  ✅ 运行中 (PID: ${PID})"
    curl -s -o /dev/null -w "  HTTP状态: %{http_code}\n" http://localhost:3001
else
    echo "  ❌ 未运行"
fi

echo ""
echo "[Python OEA] 端口 8765:"
PID=$(lsof -ti :8765)
if [ -n "${PID}" ]; then
    echo "  ✅ 运行中 (PID: ${PID})"
    STATUS=$(curl -s -w "%{http_code}" http://localhost:8765/api/open-earth/knowledge/stats)
    echo "  HTTP状态: ${STATUS}"
else
    echo "  ❌ 未运行"
fi

echo ""
echo "[Vite 前端] 端口 5173:"
PID=$(lsof -ti :5173)
if [ -n "${PID}" ]; then
    echo "  ✅ 运行中 (PID: ${PID})"
    curl -s -o /dev/null -w "  HTTP状态: %{http_code}\n" http://localhost:5173
else
    echo "  ❌ 未运行"
fi

echo ""
echo "=============================================="
