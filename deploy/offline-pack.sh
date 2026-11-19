#!/bin/bash
set -e

echo "=============================================="
echo "  RS-Agent 离线打包脚本"
echo "=============================================="
echo ""

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(dirname "${SCRIPT_DIR}")
PACK_DIR="${PROJECT_DIR}/offline-package"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="rs-agent-offline-${TIMESTAMP}.tar.gz"
INCLUDE_NODE_MODULES=${INCLUDE_NODE_MODULES:-0}
SKIP_BUILD=${SKIP_BUILD:-1}

echo "[1/5] 创建打包目录..."
rm -rf "${PACK_DIR}"
mkdir -p "${PACK_DIR}"

echo ""
echo "[2/5] 复制项目文件..."
echo "  复制源代码..."
cp -r "${PROJECT_DIR}/src" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/ui" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/open-earth-engine" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/rs-engine" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/products" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/scripts" "${PACK_DIR}/"
cp -r "${PROJECT_DIR}/deploy" "${PACK_DIR}/"

echo "  复制配置文件..."
cp "${PROJECT_DIR}/package.json" "${PACK_DIR}/"
cp "${PROJECT_DIR}/tsconfig.json" "${PACK_DIR}/"
cp "${PROJECT_DIR}/README.md" "${PACK_DIR}/"
cp "${PROJECT_DIR}/README.zh.md" "${PACK_DIR}/"
cp "${PROJECT_DIR}/pnpm-workspace.yaml" "${PACK_DIR}/" 2>/dev/null || true
cp "${PROJECT_DIR}/package-lock.json" "${PACK_DIR}/" 2>/dev/null || true

echo ""
echo "[3/5] 复制 Node.js 依赖..."
if [ "${INCLUDE_NODE_MODULES}" = "1" ]; then
    if [ -d "${PROJECT_DIR}/node_modules" ]; then
        echo "  复制根目录 node_modules..."
        cp -r "${PROJECT_DIR}/node_modules" "${PACK_DIR}/"
    fi
    if [ -d "${PROJECT_DIR}/ui/node_modules" ]; then
        echo "  复制 ui/node_modules..."
        mkdir -p "${PACK_DIR}/ui"
        cp -r "${PROJECT_DIR}/ui/node_modules" "${PACK_DIR}/ui/"
    fi
    echo "  ✅ 已包含 node_modules"
else
    echo "  ⚠️  未包含 node_modules（目标服务器需要运行 install.sh 安装）"
    echo "  如需包含，设置环境变量: INCLUDE_NODE_MODULES=1"
fi

echo ""
echo "[4/5] 预构建前端项目..."
cd "${PACK_DIR}/ui"
if [ -d "node_modules" ] || [ "${SKIP_BUILD}" = "0" ]; then
    if [ "${SKIP_BUILD}" = "0" ]; then
        echo "  构建前端..."
        npm run build 2>/dev/null || echo "  ⚠️  前端构建跳过（依赖缺失）"
    else
        echo "  已包含 node_modules，跳过构建"
    fi
else
    echo "  ⚠️  跳过构建（需先安装 node_modules）"
fi

echo ""
echo "[5/5] 打包压缩..."
cd "${PROJECT_DIR}"
rm -f "${PACKAGE_NAME}"
tar -czvf "${PACKAGE_NAME}" -C "${PACK_DIR}" .

echo ""
echo "=============================================="
echo "  打包完成！"
echo "=============================================="
echo ""
echo "包路径: ${PROJECT_DIR}/${PACKAGE_NAME}"
echo "包大小: $(du -h "${PROJECT_DIR}/${PACKAGE_NAME}" | cut -f1)"
echo ""
echo "部署步骤:"
echo "  1. 将 ${PACKAGE_NAME} 上传到目标服务器"
echo "  2. 解压: tar -xzvf ${PACKAGE_NAME}"
echo "  3. 安装依赖: bash deploy/install.sh"
echo "  4. 启动服务: bash deploy/start.sh"
echo ""
echo "提示:"
echo "  - 如需包含 node_modules: INCLUDE_NODE_MODULES=1 bash deploy/offline-pack.sh"
echo "  - 包内已包含 deploy/ 目录下的所有部署脚本"
