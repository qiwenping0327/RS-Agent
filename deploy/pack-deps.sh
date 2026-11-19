#!/bin/bash
set -e

echo "=============================================="
echo "  RS-Agent 环境依赖离线打包脚本"
echo "=============================================="
echo ""

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(dirname "${SCRIPT_DIR}")
DEPS_DIR="${PROJECT_DIR}/dependencies"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

PACK_NODE_MODULES="${DEPS_DIR}/node_modules-${TIMESTAMP}.tar.gz"
PACK_PIP_DEPS="${DEPS_DIR}/pip-deps-${TIMESTAMP}.tar.gz"
PACK_NODE_RUNTIME="${DEPS_DIR}/node-runtime-${TIMESTAMP}.tar.gz"

echo "[1/5] 创建依赖目录..."
mkdir -p "${DEPS_DIR}"
echo "  依赖目录: ${DEPS_DIR}"

echo ""
echo "[2/5] 打包 Node.js 依赖（node_modules）..."
echo "  打包根目录 node_modules..."
if [ -d "${PROJECT_DIR}/node_modules" ]; then
    tar -czf "${DEPS_DIR}/node_modules-root-tmp.tar.gz" -C "${PROJECT_DIR}" node_modules
    echo "  ✅ 根目录 node_modules 已打包"
else
    echo "  ⚠️  根目录 node_modules 不存在，跳过"
fi

echo "  打包 ui/node_modules..."
if [ -d "${PROJECT_DIR}/ui/node_modules" ]; then
    tar -czf "${DEPS_DIR}/node_modules-ui-tmp.tar.gz" -C "${PROJECT_DIR}/ui" node_modules
    echo "  ✅ ui/node_modules 已打包"
else
    echo "  ⚠️  ui/node_modules 不存在，跳过"
fi

echo ""
echo "[3/5] 打包 Python 依赖（pip wheels）..."
PIP_DOWNLOAD_DIR="${DEPS_DIR}/pip-downloads"
rm -rf "${PIP_DOWNLOAD_DIR}"
mkdir -p "${PIP_DOWNLOAD_DIR}/open-earth-engine"
mkdir -p "${PIP_DOWNLOAD_DIR}/rs-engine"

echo "  下载 open-earth-engine 依赖..."
pip download -d "${PIP_DOWNLOAD_DIR}/open-earth-engine" \
    -r "${PROJECT_DIR}/open-earth-engine/requirements.txt" \
    --python-version 3.10 --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
pip download -d "${PIP_DOWNLOAD_DIR}/open-earth-engine" \
    -r "${PROJECT_DIR}/open-earth-engine/requirements.txt" 2>/dev/null || \
echo "  ⚠️  open-earth-engine 依赖下载失败，请检查网络"

echo "  下载 rs-engine 依赖..."
pip download -d "${PIP_DOWNLOAD_DIR}/rs-engine" \
    -r "${PROJECT_DIR}/rs-engine/requirements.txt" \
    --python-version 3.10 --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
pip download -d "${PIP_DOWNLOAD_DIR}/rs-engine" \
    -r "${PROJECT_DIR}/rs-engine/requirements.txt" 2>/dev/null || \
echo "  ⚠️  rs-engine 依赖下载失败，请检查网络"

echo "  压缩 pip 依赖..."
cd "${DEPS_DIR}"
tar -czf "pip-deps-${TIMESTAMP}.tar.gz" -C "${DEPS_DIR}" pip-downloads
echo "  ✅ Python 依赖已打包: pip-deps-${TIMESTAMP}.tar.gz"

echo ""
echo "[4/5] 打包 Node.js 运行时..."
NODE_BIN_PATH="/root/.workbuddy/binaries/node/versions/22.12.0"
if [ -d "${NODE_BIN_PATH}" ]; then
    echo "  打包 Node.js 运行时（${NODE_BIN_PATH}）..."
    tar -czf "${PACK_NODE_RUNTIME}" -C "$(dirname ${NODE_BIN_PATH})" "$(basename ${NODE_BIN_PATH})"
    echo "  ✅ Node.js 运行时已打包: $(basename ${PACK_NODE_RUNTIME})"
else
    echo "  ⚠️  Node.js 运行时路径不存在: ${NODE_BIN_PATH}"
    echo "      目标服务器需要单独安装 Node.js"
fi

echo ""
echo "[5/5] 合并所有依赖包..."
echo "  创建总依赖包..."

# 创建总目录
TOTAL_DIR="${DEPS_DIR}/rs-agent-deps-${TIMESTAMP}"
rm -rf "${TOTAL_DIR}"
mkdir -p "${TOTAL_DIR}"

# 复制 node_modules
if [ -f "${DEPS_DIR}/node_modules-root-tmp.tar.gz" ]; then
    mv "${DEPS_DIR}/node_modules-root-tmp.tar.gz" "${TOTAL_DIR}/"
fi
if [ -f "${DEPS_DIR}/node_modules-ui-tmp.tar.gz" ]; then
    mv "${DEPS_DIR}/node_modules-ui-tmp.tar.gz" "${TOTAL_DIR}/"
fi

# 复制 pip 依赖
if [ -f "${DEPS_DIR}/pip-deps-${TIMESTAMP}.tar.gz" ]; then
    mv "${DEPS_DIR}/pip-deps-${TIMESTAMP}.tar.gz" "${TOTAL_DIR}/"
fi

# 复制 node 运行时
if [ -f "${PACK_NODE_RUNTIME}" ]; then
    mv "${PACK_NODE_RUNTIME}" "${TOTAL_DIR}/"
fi

# 复制安装脚本
cp "${SCRIPT_DIR}/install.sh" "${TOTAL_DIR}/" 2>/dev/null || true
cp "${SCRIPT_DIR}/OFFLINE_DEPLOYMENT.md" "${TOTAL_DIR}/" 2>/dev/null || true

# 创建安装说明
cat > "${TOTAL_DIR}/README.txt" << 'EOF'
RS-Agent 环境依赖包
====================

包内容:
1. node_modules-root-tmp.tar.gz    - 根目录 Node.js 依赖
2. node_modules-ui-tmp.tar.gz      - UI 目录 Node.js 依赖
3. pip-deps-*.tar.gz                - Python 离线依赖
4. node-runtime-*.tar.gz           - Node.js 运行时（如有）

目标服务器安装步骤:
1. 将本目录上传到目标服务器
2. 解压:
   tar -xzvf node_modules-root-tmp.tar.gz -C /opt/rs-agent/
   tar -xzvf node_modules-ui-tmp.tar.gz -C /opt/rs-agent/ui/
3. 解压 Python 依赖:
   mkdir -p /tmp/pip-deps
   tar -xzvf pip-deps-*.tar.gz -C /tmp/pip-deps
4. 创建 Conda 环境并安装 Python 依赖:
   conda create -y -n rs-agent python=3.10
   conda activate rs-agent
   pip install --no-index --find-links=/tmp/pip-deps/pip-downloads/open-earth-engine -r /opt/rs-agent/open-earth-engine/requirements.txt
   pip install --no-index --find-links=/tmp/pip-deps/pip-downloads/rs-engine -r /opt/rs-agent/rs-engine/requirements.txt
5. 启动服务:
   cd /opt/rs-agent
   bash deploy/start.sh
EOF

# 打包
cd "${DEPS_DIR}"
tar -czf "rs-agent-deps-${TIMESTAMP}.tar.gz" -C "${DEPS_DIR}" "$(basename ${TOTAL_DIR})"

# 清理
rm -rf "${TOTAL_DIR}"
rm -rf "${PIP_DOWNLOAD_DIR}"

echo ""
echo "=============================================="
echo "  依赖打包完成！"
echo "=============================================="
echo ""
echo "输出文件:"
echo "  总依赖包: ${DEPS_DIR}/rs-agent-deps-${TIMESTAMP}.tar.gz"
echo "  包大小: $(du -h ${DEPS_DIR}/rs-agent-deps-${TIMESTAMP}.tar.gz | cut -f1)"
echo ""
echo "包内文件列表:"
tar -tzf "${DEPS_DIR}/rs-agent-deps-${TIMESTAMP}.tar.gz" | head -20
echo ""
echo "=============================================="
