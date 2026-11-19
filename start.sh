#!/usr/bin/env bash
set -euo pipefail

# ── RsAgent Startup Script ────────────────────────────────────────────
# Usage:
#   ./start.sh              # 开发模式 (HMR, 端口 5173)
#   ./start.sh --prod       # 生产模式 (端口 3001)
#   ./start.sh --install    # 首次安装依赖后启动
#   ./start.sh --port 8080  # 指定端口
#   ./start.sh --no-python  # 跳过 conda / Python 环境检查

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="dev"
DO_INSTALL=false
CUSTOM_PORT=""
SKIP_PYTHON=false

# ── Parse args ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod)       MODE="prod";  shift ;;
    --install)    DO_INSTALL=true; shift ;;
    --port)       CUSTOM_PORT="$2"; shift 2 ;;
    --port=*)     CUSTOM_PORT="${1#--port=}"; shift ;;
    --no-python)  SKIP_PYTHON=true; shift ;;
    -h|--help)
      echo "Usage: ./start.sh [--prod] [--install] [--port <port>] [--no-python]"
      echo ""
      echo "  --prod       生产模式 (先构建, 端口 3001)"
      echo "  --install    首次运行, 先安装依赖"
      echo "  --port       指定服务端口"
      echo "  --no-python  跳过 conda / Python 环境检查 (不启动 MCP Python 服务)"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}→${RESET} %s\n" "$1"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$1"; }
step() { printf "\n${BOLD}%s${RESET}\n" "$1"; }

# ── Step 1: Activate conda environment ────────────────────────────────
step "Step 1: 激活 conda 环境 (pilotdeck)..."

if [[ "$SKIP_PYTHON" == true ]]; then
  warn "跳过 conda 环境检查 (--no-python)"
  warn "rs-agent 等 MCP Python 服务将不可用"
else
  # CONDA_EXE may end with /bin/conda or /condabin/conda
  _conda_exe="${CONDA_EXE:-}"
  CONDA_BASE="${_conda_exe%/condabin/conda}"
  CONDA_BASE="${CONDA_BASE%/bin/conda}"
  if [[ -z "$CONDA_BASE" || ! -d "$CONDA_BASE/envs" ]]; then
    CONDA_BASE="$(conda info --base 2>/dev/null || true)"
  fi

  if [[ -n "$CONDA_BASE" && -d "$CONDA_BASE/envs/pilotdeck" ]]; then
    # Source conda's shell hook so `conda activate` works in this script
    eval "$("$CONDA_BASE/bin/conda" shell.bash hook 2>/dev/null)"
    conda activate pilotdeck
    ok "conda 环境 pilotdeck 已激活: $(which python)"

    # Verify rs-engine dependencies
    RS_ENGINE_DIR="$ROOT_DIR/rs-engine"
    if [[ -d "$RS_ENGINE_DIR" && -f "$RS_ENGINE_DIR/requirements.txt" ]]; then
      MISSING_DEPS=false
      for pkg in mcp rasterio numpy fastapi uvicorn; do
        if ! python -c "import ${pkg}" 2>/dev/null; then
          MISSING_DEPS=true
          break
        fi
      done

      if [[ "$MISSING_DEPS" == true ]]; then
        warn "检测到 rs-engine Python 依赖缺失，正在安装..."
        pip install -r "$RS_ENGINE_DIR/requirements.txt" --quiet 2>&1 | tail -3
        ok "rs-engine 依赖已安装"
      else
        ok "rs-engine Python 依赖已就绪"
      fi
    fi
  else
    warn "未找到 conda 环境 'pilotdeck'"
    warn "rs-agent 等 MCP Python 服务将不可用"
    warn "如需启用，请先创建: conda create -n pilotdeck python=3.12 && conda activate pilotdeck && pip install -r rs-engine/requirements.txt"
  fi
fi

# ── Step 2: Check Node.js ─────────────────────────────────────────────
step "Step 2: 检查 Node.js..."
if ! command -v node >/dev/null 2>&1; then
  # If conda env is active, node should be available via it
  if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/node" ]]; then
    export PATH="$CONDA_PREFIX/bin:$PATH"
    ok "Node.js (via conda: $CONDA_PREFIX)"
  else
    fail "未找到 Node.js，请先安装 Node.js >= 20"
    echo "  推荐使用: conda install -n pilotdeck nodejs  或  curl -fsSL https://fnm.vercel.app/install | bash && fnm install 22"
    exit 1
  fi
fi

NODE_VERSION=$(node --version)
NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
if [[ "$NODE_MAJOR" -lt 20 ]]; then
  fail "Node.js ${NODE_VERSION} 版本过低 (需要 >= 20)"
  exit 1
fi
ok "Node.js ${NODE_VERSION}"

# ── Step 3: Install dependencies ──────────────────────────────────────
if [[ "$DO_INSTALL" == true ]]; then
  step "Step 3: 安装依赖..."
  cd "$ROOT_DIR"
  HUSKY=0 npm install --no-audit --no-fund --loglevel=error
  ok "根目录依赖已安装"

  cd "$ROOT_DIR/ui"
  HUSKY=0 npm install --no-audit --no-fund --loglevel=error
  ok "UI 依赖已安装"
else
  if [[ ! -d "$ROOT_DIR/node_modules" || ! -d "$ROOT_DIR/ui/node_modules" ]]; then
    step "Step 3: 安装缺失依赖..."
    cd "$ROOT_DIR" && HUSKY=0 npm install --no-audit --no-fund --loglevel=error
    cd "$ROOT_DIR/ui" && HUSKY=0 npm install --no-audit --no-fund --loglevel=error
    ok "依赖已安装"
  else
    step "Step 3: 检查依赖..."
    ok "依赖已就绪"
  fi
fi

# ── Step 4: Bootstrap config & plugins ────────────────────────────────
step "Step 4: 检查配置与插件..."
cd "$ROOT_DIR"
node scripts/bootstrap-pilotdeck-config.mjs

PILOT_HOME="${PILOT_HOME:-$HOME/.pilotdeck}"
CONFIG_FILE="${PILOTDECK_CONFIG_PATH:-$PILOT_HOME/pilotdeck.yaml}"

if [[ -f "$CONFIG_FILE" ]]; then
  ok "配置文件: ${CONFIG_FILE}"
  if grep -q "PLACEHOLDER_RUN_ONBOARDING_TO_REPLACE" "$CONFIG_FILE" 2>/dev/null; then
    warn "检测到占位配置，启动后请在 Web UI 中完成模型配置 (填入 API Key)"
  fi
else
  warn "配置文件不存在: ${CONFIG_FILE}"
  warn "启动后请在 Web UI 中完成初始化配置"
fi

# Ensure rs-agent plugin is linked into BOTH project and global plugins dirs
# Global (~/.pilotdeck/plugins/) is needed so MCP servers are found from any project
# Project (.pilotdeck/plugins/) is the project-level fallback
RS_AGENT_SRC="$ROOT_DIR/products/rs-agent/plugins/rs-agent"

for PLUGINS_DIR in "$PILOT_HOME/plugins" "$ROOT_DIR/.pilotdeck/plugins"; do
  RS_AGENT_DST="$PLUGINS_DIR/rs-agent"
  if [[ -d "$RS_AGENT_SRC" && ! -e "$RS_AGENT_DST" ]]; then
    mkdir -p "$PLUGINS_DIR"
    ln -sf "$RS_AGENT_SRC" "$RS_AGENT_DST"
    ok "已链接 rs-agent 插件 → $PLUGINS_DIR/rs-agent"
  elif [[ -d "$RS_AGENT_SRC" && -L "$RS_AGENT_DST" ]]; then
    ok "rs-agent 插件链接已存在 ($PLUGINS_DIR)"
  fi
done

# ── Step 5: MCP server pre-check ──────────────────────────────────────
step "Step 5: MCP 服务器预检..."

MCP_READY=true
MCP_SERVERS=()

# Check rs-agent MCP servers (6 servers, all need python + conda)
if [[ -f "$ROOT_DIR/.pilotdeck/plugins/rs-agent/plugin.json" ]]; then
  if [[ "$SKIP_PYTHON" != true ]] && command -v python >/dev/null 2>&1; then
    if python -c "import mcp" 2>/dev/null; then
      for srv in rs-agent rs-analysis rs-index rs-inversion rs-perception rs-statistics; do
        MCP_SERVERS+=("$srv")
      done
      ok "rs-agent: 6 个 MCP 服务器就绪 (python + mcp SDK)"
    else
      warn "rs-agent: mcp SDK 未安装 — 6 个遥感 MCP 服务器不可用"
      warn "  修复: pip install mcp"
      MCP_READY=false
    fi
  else
    warn "rs-agent: Python 环境不可用 — 6 个遥感 MCP 服务器不可用"
    MCP_READY=false
  fi
fi

# Check browser-use MCP server (uses npx, auto-installed)
if [[ -f "$ROOT_DIR/src/extension/plugins/builtin/browser-use/plugin.json" ]]; then
  MCP_SERVERS+=("browser-use")
  ok "browser-use: MCP 服务器将自动启动 (npx @playwright/mcp)"
fi

if [[ ${#MCP_SERVERS[@]} -gt 0 ]]; then
  echo ""
  echo -e "  ${BOLD}MCP 服务器清单 (${#MCP_SERVERS[@]}):${RESET}"
  for srv in "${MCP_SERVERS[@]}"; do
    echo -e "    ${DIM}• ${srv}${RESET}"
  done
  if [[ "$MCP_READY" == false ]]; then
    echo ""
    warn "部分 MCP 服务器不可用，系统仍可启动但功能受限"
  fi
else
  warn "未检测到 MCP 服务器，启动后 Agent 将只有内置工具"
fi

# ── Step 6: Resolve ports ─────────────────────────────────────────────
resolve_port() {
  local base="$1"
  if [[ -n "$CUSTOM_PORT" ]]; then
    echo "$CUSTOM_PORT"
    return
  fi
  for offset in $(seq 0 20); do
    local candidate=$((base + offset))
    if ! (echo >/dev/tcp/127.0.0.1/"$candidate") 2>/dev/null; then
      echo "$candidate"
      return
    fi
  done
  echo "$base"
}

# ── Step 7: Start services ────────────────────────────────────────────
cd "$ROOT_DIR"

if [[ "$MODE" == "prod" ]]; then
  step "Step 7: 🚀 生产模式启动..."
else
  step "Step 7: 🚀 开发模式启动..."
fi

SERVER_PORT=$(resolve_port 3001)
GATEWAY_PORT=$(resolve_port 18789)
VITE_PORT=$(resolve_port 5173)

export SERVER_PORT
export PILOTDECK_GATEWAY_PORT=$GATEWAY_PORT
export PILOTDECK_GATEWAY_URL="ws://127.0.0.1:${GATEWAY_PORT}/ws"
export VITE_PORT
export PILOTDECK_SKIP_DEFAULT_PROJECT=1

echo ""
echo -e "  ${BOLD}═══════════════════════════════════════════════${RESET}"
echo -e "  ${BOLD}  RsAgent 已启动${RESET}"
echo -e "  ${BOLD}═══════════════════════════════════════════════${RESET}"
if [[ "$MODE" == "prod" ]]; then
  echo -e "  ${BOLD}访问地址:${RESET}  ${DIM}http://localhost:${SERVER_PORT}${RESET}"
else
  echo -e "  ${BOLD}访问地址:${RESET}  ${DIM}http://localhost:${VITE_PORT}${RESET}"
fi
echo -e "  ${BOLD}Gateway:${RESET}    ${DIM}ws://127.0.0.1:${GATEWAY_PORT}/ws${RESET}"
echo -e "  ${BOLD}模式:${RESET}        ${DIM}$([ "$MODE" == "prod" ] && echo '生产' || echo '开发 (HMR)')${RESET}"
echo -e "  ${BOLD}MCP 服务:${RESET}   ${DIM}${#MCP_SERVERS[@]} 个${RESET}"
echo -e "  ${BOLD}═══════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${YELLOW}提示: MCP 工具在首次对话时懒加载启动，请稍候片刻${RESET}"
echo ""

if [[ "$MODE" == "prod" ]]; then
  cd "$ROOT_DIR/ui"
  exec npm run start
else
  cd "$ROOT_DIR/ui"
  exec npx concurrently --kill-others-on-fail --names gateway,server,client \
    "npm run dev:gateway" \
    "npm run dev:server" \
    "npm run dev:client"
fi
