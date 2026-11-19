# RS-Agent 离线部署方案

## 一、系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04 LTS (64位) |
| CPU | 4核及以上 |
| 内存 | 8GB及以上 |
| 磁盘 | 50GB及以上 |
| 网络 | 无需外网（离线部署） |

## 二、离线准备工作（有网络环境）

### 2.1 下载 Node.js

```bash
# 下载 Node.js 22.12.0
wget https://nodejs.org/dist/v22.12.0/node-v22.12.0-linux-x64.tar.xz

# 解压
tar -xJvf node-v22.12.0-linux-x64.tar.xz
```

### 2.2 下载 Miniconda

```bash
# 下载 Miniconda (Python 3.10)
wget https://repo.anaconda.com/miniconda/Miniconda3-py310_23.11.0-2-Linux-x86_64.sh
```

### 2.3 下载 Python 依赖（离线安装包）

```bash
# 创建离线依赖目录
mkdir -p /tmp/pip-offline

# 在有网络环境的机器上下载依赖
cd /path/to/PilotDeck
source /path/to/miniconda3/etc/profile.d/conda.sh
conda create -y -n rs-agent python=3.10
conda activate rs-agent

# 下载 open-earth-engine 依赖
pip download -d /tmp/pip-offline/open-earth-engine -r open-earth-engine/requirements.txt

# 下载 rs-engine 依赖
pip download -d /tmp/pip-offline/rs-engine -r rs-engine/requirements.txt

# 打包
cd /tmp/pip-offline
tar -czvf pip-dependencies.tar.gz .
```

### 2.4 下载 npm 依赖（可选）

```bash
# 在有网络环境的机器上安装依赖
cd /path/to/PilotDeck
npm install --legacy-peer-deps
cd ui
npm install --legacy-peer-deps

# 构建项目
cd ..
npm run build
cd ui
npm run build

# 打包整个项目（包含 node_modules）
cd ..
bash deploy/offline-pack.sh
```

## 三、目标服务器部署步骤

### 3.1 安装基础系统依赖

```bash
sudo apt update
sudo apt install -y build-essential libssl-dev libffi-dev \
    python3-dev python3-pip \
    nginx lsof curl wget \
    libgdal-dev libgeos-dev libproj-dev
```

### 3.2 安装 Node.js

```bash
# 将下载的 node-v22.12.0-linux-x64.tar.xz 上传到服务器
tar -xJvf node-v22.12.0-linux-x64.tar.xz
sudo mv node-v22.12.0-linux-x64 /opt/

# 添加到 PATH（永久生效）
echo 'export PATH="/opt/node-v22.12.0-linux-x64/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证
node --version
npm --version
```

### 3.3 安装 Miniconda

```bash
# 将下载的 Miniconda3-py310_23.11.0-2-Linux-x86_64.sh 上传到服务器
bash Miniconda3-py310_23.11.0-2-Linux-x86_64.sh -b -p /root/miniconda3

# 添加到 PATH（永久生效）
echo 'export PATH="/root/miniconda3/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证
conda --version
```

### 3.4 创建 Conda 环境并安装 Python 依赖

```bash
# 创建环境
conda create -y -n rs-agent python=3.10

# 激活环境
conda activate rs-agent

# 离线安装 Python 依赖
tar -xzvf pip-dependencies.tar.gz
pip install --no-index --find-links=open-earth-engine -r /path/to/open-earth-engine/requirements.txt
pip install --no-index --find-links=rs-engine -r /path/to/rs-engine/requirements.txt
```

### 3.5 上传并解压项目包

```bash
# 将离线包上传到服务器
tar -xzvf rs-agent-offline-xxx.tar.gz -C /opt/
mv /opt/rs-agent-offline-xxx /opt/rs-agent

# 进入项目目录
cd /opt/rs-agent
```

### 3.6 安装 Node.js 依赖（如果离线包未包含 node_modules）

```bash
# 如果离线包中未包含 node_modules，需要在有网络环境提前下载
# 将 node_modules 目录打包上传后解压即可

# 或者如果服务器可以临时访问外网：
npm install --legacy-peer-deps
cd ui
npm install --legacy-peer-deps
```

### 3.7 构建项目（如果离线包未预构建）

```bash
# 构建后端
cd /opt/rs-agent
npm run build

# 构建前端
cd ui
npm run build
```

### 3.8 启动服务

```bash
# 方法一：使用启动脚本
bash deploy/start.sh

# 方法二：使用 systemd 服务
cp deploy/rs-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable rs-agent
systemctl start rs-agent

# 查看状态
systemctl status rs-agent
```

## 四、服务管理

### 4.1 启动服务

```bash
bash deploy/start.sh
```

### 4.2 停止服务

```bash
bash deploy/stop.sh
```

### 4.3 查看服务状态

```bash
bash deploy/status.sh
```

### 4.4 查看日志

```bash
# Gateway 日志
tail -f /var/log/rs-agent/gateway.log

# Express 日志
tail -f /var/log/rs-agent/express.log

# Python OEA 日志
tail -f /var/log/rs-agent/oea-service.log

# Vite 日志
tail -f /var/log/rs-agent/vite.log

# systemd 日志
journalctl -u rs-agent -f
```

## 五、服务端口

| 服务 | 端口 | 用途 |
|------|------|------|
| Gateway | 18789 | 智能体通信网关 |
| Express | 3001 | 后端 API 服务 |
| Python OEA | 8765 | 遥感任务执行服务 |
| Vite | 5173 | 前端开发服务器 |

## 六、目录结构

```
/opt/rs-agent/
├── src/                    # 后端源代码
├── ui/                     # 前端代码
│   ├── src/               # 前端源代码
│   ├── server/            # Express 服务器
│   ├── dist/              # 前端构建产物
│   └── node_modules/      # Node.js 依赖
├── open-earth-engine/     # OpenEarthEngine Python 服务
├── rs-engine/             # 遥感引擎 Python 服务
├── products/              # 产品配置
├── scripts/               # 脚本工具
├── deploy/                # 部署脚本
│   ├── install.sh         # 安装脚本
│   ├── start.sh           # 启动脚本
│   ├── stop.sh            # 停止脚本
│   ├── status.sh          # 状态检查脚本
│   ├── rs-agent.service   # systemd 服务配置
│   └── offline-pack.sh    # 离线打包脚本
└── dist/                  # 后端构建产物

/data/rs-agent/
├── test_scenes/           # 测试影像数据
├── oea_output/            # 任务输出结果
└── knowledge/             # 知识库数据

/var/log/rs-agent/
├── gateway.log            # Gateway 日志
├── express.log            # Express 日志
├── oea-service.log        # Python OEA 日志
└── vite.log               # Vite 日志
```

## 七、配置文件

### 7.1 pilotdeck.yaml

```yaml
# ~/.pilotdeck/pilotdeck.yaml
webui:
  runtime:
    serverPort: 3001
    vitePort: 5173
```

### 7.2 LLM 配置

```yaml
# ~/.pilotdeck/pilotdeck.yaml
llm:
  provider: openai
  api_base: http://your-llm-proxy:8080/v1
  api_key: your-api-key
  model: deepseek-v4-pro
```

## 八、安全建议

1. **防火墙配置**：仅开放必要端口（5173 或 Nginx 代理端口）
2. **HTTPS**：建议使用 Nginx 反向代理并配置 SSL 证书
3. **访问控制**：通过 Nginx 配置 IP 白名单
4. **定期备份**：定期备份数据库和知识库文件

## 九、Nginx 反向代理配置（推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }
}
```

## 十、故障排查

### 10.1 服务启动失败

```bash
# 检查端口是否被占用
lsof -i :5173 -i :3001 -i :8765 -i :18789

# 检查日志
bash deploy/status.sh
```

### 10.2 Python 依赖安装失败

```bash
# 确保 GDAL 开发库已安装
sudo apt install -y libgdal-dev

# 设置 GDAL 环境变量
export C_INCLUDE_PATH=/usr/include/gdal
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export GDAL_CONFIG=/usr/bin/gdal-config

# 重新安装
pip install GDAL==$(gdal-config --version)
```

### 10.3 Node.js 原生模块编译失败

```bash
# 安装编译工具
sudo apt install -y build-essential python3-dev

# 重新安装
npm rebuild
```

### 10.4 前端页面无法访问

```bash
# 检查 Vite 服务状态
curl http://localhost:5173

# 检查 Nginx 配置
nginx -t
systemctl restart nginx
```

## 十一、版本更新

```bash
# 1. 停止服务
bash deploy/stop.sh

# 2. 备份数据
tar -czvf rs-agent-backup-$(date +%Y%m%d).tar.gz /data/rs-agent

# 3. 更新代码
tar -xzvf rs-agent-offline-new.tar.gz -C /opt/

# 4. 重新构建
cd /opt/rs-agent
npm run build
cd ui
npm run build

# 5. 启动服务
bash deploy/start.sh
```
