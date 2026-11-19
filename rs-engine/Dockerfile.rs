# 遥感智能分析 Agent - Docker 镜像
# 多阶段构建: 基础依赖 + 遥感库 + 应用代码

# ---------------------------------------------------------------------------
# 阶段 1: 基础依赖 + GDAL
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_CONFIG=/usr/bin/gdal-config

# ---------------------------------------------------------------------------
# 阶段 2: Python 依赖安装
# ---------------------------------------------------------------------------
FROM base AS dependencies

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

# 尝试安装 GDAL Python 绑定（版本匹配可能失败，忽略错误）
RUN GDAL_VERSION=$(gdal-config --version 2>/dev/null || echo "3.6.0") && \
    pip install --no-cache-dir GDAL==${GDAL_VERSION}.* || true

# ---------------------------------------------------------------------------
# 阶段 3: 应用代码
# ---------------------------------------------------------------------------
FROM base AS runtime

WORKDIR /opt/rs-engine

# 从依赖阶段复制已安装的包
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# 复制应用代码
COPY rs_engine/ ./rs_engine/
COPY data/ ./data/
COPY check_rs_env.py .

# 工作空间
RUN mkdir -p /workspace
ENV RS_ENGINE_HOME=/opt/rs-engine
ENV RS_WORKSPACE=/workspace
ENV RS_HOOK_PORT=8000
ENV PYTHONPATH=/opt/rs-engine

# 模型目录
RUN mkdir -p /opt/rs-engine/models

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import rs_engine; print('ok')" || exit 1

# 默认启动 MCP Server (stdio)
CMD ["python", "-m", "rs_engine.mcp_server"]
