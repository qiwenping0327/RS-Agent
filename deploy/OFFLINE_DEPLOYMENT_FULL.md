# RS-Agent 离线部署方案

## 目录

1. [离线包清单](#1-离线包清单)
2. [前置条件](#2-前置条件)
3. [部署步骤](#3-部署步骤)
4. [验证安装](#4-验证安装)
5. [服务管理](#5-服务管理)
6. [故障排查](#6-故障排查)

---

## 1. 离线包清单

> **说明**：`dependencies/` 下的 conda 环境、Node 运行时与离线依赖包**不随
> GitHub 源码仓库发布**，源码仓库只包含代码与声明文件。离线包由内部构建产物
> 或 GitHub Releases 单独分发；获取后按本文档放置到 `/root/PilotDeck/dependencies/`
> 或目标服务器的 `/tmp/deps/`。

### 1.1 需要准备的离线包

| 序号 | 包名 | 大小 | 位置 | 用途 |
|:---:|------|------|------|------|
| 1 | Miniconda3-py310_23.11.0-2-Linux-x86_64.sh | ~50MB | 需单独下载 | Python 环境管理器 |
| 2 | rs-agent-offline-20260621_221147.tar.gz | 15MB | /root/PilotDeck/ | 项目源代码 |
| 3 | rs-agent-full-deps.tar.gz | 766MB | /root/PilotDeck/dependencies/ | **完整环境依赖** |

### 1.2 rs-agent-full-deps.tar.gz 内部结构

解压后目录：`full-deps/`

| 文件 | 大小 | 说明 |
|------|------|------|
| rs-agent-conda-env.tar.gz | 291MB | Conda 完整环境（Python 3.10 + GDAL 3.11 + 所有 pip 依赖） |
| node_modules-root-tmp.tar.gz | 413MB | 根目录 Node.js 依赖 |
| node_modules-ui-tmp.tar.gz | 9.8MB | UI 目录 Node.js 依赖 |
| node-runtime-20260621_221506.tar.gz | 57MB | Node.js 运行时 v22.12.0 |
| install.sh | 4KB | 安装脚本 |
| OFFLINE_DEPLOYMENT.md | 12KB | 部署文档 |
| README.txt | 4KB | 安装说明 |

### 1.3 包获取方式

**方式一：从打包环境复制（推荐）**

```bash
# 在有网络的打包环境执行
scp user@build-server:/root/PilotDeck/rs-agent-offline-20260621_221147.tar.gz .
scp user@build-server:/root/PilotDeck/dependencies/rs-agent-full-deps.tar.gz .
```

**方式二：手动下载 Miniconda**

```bash
# 在有网络环境执行
wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh
```

---

## 2. 前置条件

### 2.1 目标服务器要求

- **操作系统**: Ubuntu 22.04 LTS (64位)
- **内存**: 至少 8GB
- **磁盘空间**: 至少 10GB（安装后约 3GB）
- **网络**: 无（完全离线部署）

### 2.2 需要安装的系统依赖（Ubuntu）

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    libssl-dev \
    nginx \
    lsof \
    tar \
    gzip
```

---

## 3. 部署步骤

### 步骤 0：准备工作

将以下文件上传到目标服务器的 `/tmp/deploy/` 目录：

```
/tmp/deploy/
├── Miniconda3-py310_23.11.0-2-Linux-x86_64.sh   # Conda 安装脚本
├── rs-agent-offline-20260621_221147.tar.gz       # 项目源代码
└── rs-agent-full-deps.tar.gz                      # 完整环境依赖
```

```bash
# 在目标服务器执行
mkdir -p /tmp/deploy
# 将上述文件上传到 /tmp/deploy/
```

---

### 步骤 1：安装 Miniconda

**安装文件**: `/tmp/deploy/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh`

```bash
# 安装 Miniconda 到 /opt/miniconda3
bash /tmp/deploy/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -b -p /opt/miniconda3

# 初始化 Conda
source /opt/miniconda3/etc/profile.d/conda.sh

# 验证安装
conda --version
# 应输出: conda 26.3.2 或更高版本
```

---

### 步骤 2：解压完整环境依赖

**解压文件**: `/tmp/deploy/rs-agent-full-deps.tar.gz`

```bash
# 解压依赖包到临时目录
mkdir -p /tmp/deps
tar -xzf /tmp/deploy/rs-agent-full-deps.tar.gz -C /tmp/deps

# 验证解压内容
ls -la /tmp/deps/full-deps/
# 应看到: rs-agent-conda-env.tar.gz, node_modules-root-tmp.tar.gz, node-runtime-*.tar.gz 等
```

---

### 步骤 3：安装 Conda 环境

**安装文件**: `/tmp/deps/full-deps/rs-agent-conda-env.tar.gz`

```bash
# 创建 Conda 环境目录
mkdir -p /opt/miniconda3/envs/rs-agent

# 解压 Conda 环境
tar -xzf /tmp/deps/full-deps/rs-agent-conda-env.tar.gz -C /opt/miniconda3/envs/rs-agent

# 激活环境
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate /opt/miniconda3/envs/rs-agent

# 验证 Python 版本
python --version
# 应输出: Python 3.10.20

# 验证 GDAL
python -c "import gdal; print(gdal.__version__)"
# 应输出: 3.11.4

# 验证关键依赖
python -c "import rasterio; import geopandas; import shapely; print('✅ 所有 Python 依赖安装成功')"
```

---

### 步骤 4：安装 Node.js 运行时

**安装文件**: `/tmp/deps/full-deps/node-runtime-20260621_221506.tar.gz`

```bash
# 解压 Node.js 到 /opt
tar -xzf /tmp/deps/full-deps/node-runtime-20260621_221506.tar.gz -C /opt/

# 添加到 PATH
export PATH="/opt/node-v22.12.0-linux-x64/bin:$PATH"

# 验证安装
node --version
# 应输出: v22.12.0

npm --version
# 应输出: 10.8.3 或更高版本
```

---

### 步骤 5：部署项目代码

**部署文件**: `/tmp/deploy/rs-agent-offline-20260621_221147.tar.gz`

```bash
# 创建项目目录
mkdir -p /opt/rs-agent

# 解压项目代码
tar -xzf /tmp/deploy/rs-agent-offline-20260621_221147.tar.gz -C /opt/rs-agent

# 查看项目结构
ls -la /opt/rs-agent/
# 应看到: src/, ui/, open-earth-engine/, rs-engine/, products/, deploy/ 等
```

---

### 步骤 6：安装 Node.js 依赖

**安装文件**: `/tmp/deps/full-deps/node_modules-root-tmp.tar.gz`  
**安装文件**: `/tmp/deps/full-deps/node_modules-ui-tmp.tar.gz`

```bash
# 安装根目录 node_modules
cd /opt/rs-agent
tar -xzf /tmp/deps/full-deps/node_modules-root-tmp.tar.gz

# 安装 UI 目录 node_modules
cd /opt/rs-agent/ui
tar -xzf /tmp/deps/full-deps/node_modules-ui-tmp.tar.gz

# 验证安装
ls -la /opt/rs-agent/node_modules/.bin/ | head -5
ls -la /opt/rs-agent/ui/node_modules/.bin/ | head -5
```

---

### 步骤 7：配置环境变量（可选）

```bash
# 编辑 /etc/profile 添加环境变量
cat >> /etc/profile << 'EOF'
export PATH="/opt/node-v22.12.0-linux-x64/bin:$PATH"
export PATH="/opt/miniconda3/bin:$PATH"
export RS_AGENT_HOME="/opt/rs-agent"
