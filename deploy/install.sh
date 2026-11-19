#!/bin/bash
set -e

echo "=============================================="
echo "  RS-Agent 离线部署安装脚本"
echo "=============================================="
echo ""

DEPLOY_DIR="/opt/rs-agent"
DATA_DIR="/data/rs-agent"
LOG_DIR="/var/log/rs-agent"
NODE_VERSION="22.12.0"
NODE_BIN="/opt/node-v${NODE_VERSION}-linux-x64/bin"

echo "[1/5] 创建目录结构..."
mkdir -p "${DEPLOY_DIR}"
mkdir -p "${DATA_DIR}/test_scenes"
mkdir -p "${DATA_DIR}/oea_output"
mkdir -p "${DATA_DIR}/knowledge"
mkdir -p "${LOG_DIR}"

echo "[2/5] 检查 Node.js 环境..."
if [ -d "${NODE_BIN}" ]; then
    echo "  Node.js 已安装: ${NODE_BIN}"
else
    echo "  请先安装 Node.js ${NODE_VERSION} 到 ${NODE_BIN}"
    echo "  下载地址: https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz"
    exit 1
fi

export PATH="${NODE_BIN}:${PATH}"
NODE_VERSION=$(node --version)
echo "  使用 Node.js: ${NODE_VERSION}"

echo ""
echo "[3/5] 安装 Python Conda 环境..."
if ! command -v conda &> /dev/null; then
    echo "  请先安装 Miniconda/Anaconda"
    exit 1
fi

CONDA_ENV_NAME="rs-agent"
if conda info --envs | grep -q "${CONDA_ENV_NAME}"; then
    echo "  Conda 环境 ${CONDA_ENV_NAME} 已存在，跳过创建"
else
    echo "  创建 Conda 环境 ${CONDA_ENV_NAME}..."
    conda create -y -n "${CONDA_ENV_NAME}" python=3.10
fi

echo "  安装 Python 依赖..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV_NAME}"

echo "  安装 open-earth-engine 依赖..."
pip install -r open-earth-engine/requirements.txt

echo "  安装 rs-engine 依赖..."
pip install -r rs-engine/requirements.txt

echo ""
echo "[4/5] 安装 Node.js 依赖..."
echo "  安装根目录依赖..."
npm install --legacy-peer-deps

echo "  安装 ui 目录依赖..."
cd ui
npm install --legacy-peer-deps

echo ""
echo "[5/5] 构建前端..."
npm run build

echo ""
echo "=============================================="
echo "  安装完成！"
echo "=============================================="
echo ""
echo "部署目录: ${DEPLOY_DIR}"
echo "数据目录: ${DATA_DIR}"
echo "日志目录: ${LOG_DIR}"
echo ""
echo "启动命令:"
echo "  cd ${DEPLOY_DIR}"
echo "  bash deploy/start.sh"
echo ""
echo "停止命令:"
echo "  bash deploy/stop.sh"
