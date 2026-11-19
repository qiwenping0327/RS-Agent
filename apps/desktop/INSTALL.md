# RsAgent Desktop —— Windows 安装指南

## 一、系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10 64位 / Windows 11 |
| 架构 | x64 |
| 磁盘空间 | ≥ 1 GB（安装后运行时解压约占 500 MB） |
| 内存 | ≥ 8 GB |
| Python | 3.10+（MCP 遥感工具和知识库服务依赖） |
| 网络 | 需要访问 DeepSeek API（`https://api.deepseek.com`） |

## 二、安装步骤

### 1. 运行安装程序

双击 `RsAgent-0.0.11-win-x64.exe`，按照 NSIS 安装向导完成安装。

默认安装路径：`C:\Users\<用户名>\AppData\Local\RsAgent`

### 2. 首次启动

安装完成后，从开始菜单或桌面快捷方式启动 RsAgent。

首次启动时，应用会自动将运行时资源（bundle tar 文件）解压到：
```
C:\Users\<用户名>\AppData\Roaming\RsAgent\runtime\0.0.11\
```

此过程约需 10-30 秒，请耐心等待。解压完成后，应用会自动启动本地服务。

### 3. 配置 Python 环境（MCP 工具依赖）

RsAgent 的遥感 MCP 工具（rs-agent、rs-analysis、rs-index、rs-inversion、rs-perception、rs-statistics）和知识库服务依赖 Python 3.10+。

#### 3.1 安装 Python

如果尚未安装 Python，请从以下任一渠道安装：
- **Miniconda**（推荐）：https://docs.conda.io/en/latest/miniconda.html
- **Python 官方**：https://www.python.org/downloads/

安装时请勾选 **"Add Python to PATH"**。

#### 3.2 安装 Python 依赖

打开命令行（PowerShell 或 CMD），执行：

```bash
pip install fastmcp mcp aiohttp numpy
```

如果使用 Miniconda/Anaconda：
```bash
conda install -c conda-forge aiohttp numpy
pip install fastmcp mcp
```

#### 3.3 配置 Python 路径

如果 Python 不在系统 PATH 中，需要设置环境变量 `PILOTDECK_CONDA_PYTHON` 指向 Python 可执行文件路径：

```
setx PILOTDECK_CONDA_PYTHON "D:\miniconda3\python.exe"
```

设置后需要**重启 RsAgent** 才能生效。

### 4. 配置 AI 模型

首次启动后，如果无法正常对话，需要配置 DeepSeek API：

1. 打开 RsAgent 设置页面（点击左下角设置图标）
2. 在"模型配置"中填写：
   - **模型提供商**：OpenAI 协议
   - **API 地址**：`https://api.deepseek.com/v1`
   - **API Key**：你的 DeepSeek API Key（在 https://platform.deepseek.com 获取）
   - **模型名称**：`deepseek-v4-flash`

或直接编辑配置文件 `C:\Users\<用户名>\.rsagent\pilotdeck.yaml`：

```yaml
schemaVersion: 1
agent:
  model: rsagent/deepseek-v4-flash
model:
  providers:
    rsagent:
      protocol: openai
      url: "https://api.deepseek.com/v1"
      apiKey: "sk-你的API密钥"
      models:
        deepseek-v4-flash: {}
```

## 三、验证安装

启动 RsAgent 后，请检查以下功能是否正常：

| 功能 | 验证方法 | 预期结果 |
|---|---|---|
| 本地服务 | 应用正常进入主界面，无"本地服务启动失败"弹窗 | Gateway 监听 18789 端口，UI 监听 18790 端口 |
| AI 对话 | 在聊天框发送"你好" | 收到模型回复 |
| MCP 工具 | 查看 MCP 工具面板 | 显示 8 个 MCP 服务器（browser-use + 7 个遥感工具） |
| 知识库 | 查看知识库面板 | 显示 13 条知识条目 |

## 四、常见问题

### Q1: 启动时报"本地服务启动失败"

**可能原因及解决方案：**

1. **Python 未安装或路径不对**
   - 确认 Python 3.10+ 已安装
   - 设置环境变量 `PILOTDECK_CONDA_PYTHON` 指向 Python 路径
   - 重启 RsAgent

2. **Python 依赖缺失**
   - 执行 `pip install fastmcp mcp aiohttp numpy`
   - 重启 RsAgent

3. **API Key 未配置或无效**
   - 检查 `.rsagent/pilotdeck.yaml` 中的 API Key
   - 确认 API 地址为 `https://api.deepseek.com/v1`

4. **查看详细日志**
   - 日志文件位于：`C:\Users\<用户名>\.rsagent\desktop.server.log`
   - 查看末尾的报错信息

### Q2: MCP 工具不显示

确认以下目录存在且包含插件文件：
```
C:\Users\<用户名>\.rsagent\plugins\
```

如果为空，尝试重新安装 RsAgent（安装包会自动解压插件到 runtime 目录）。

### Q3: 知识库为空

知识库服务依赖 Python。确认：
1. Python 服务已在端口 8765 上运行
2. Python 依赖（`aiohttp`、`numpy`）已安装

### Q4: 安装后源码是否会被他人获取

不会。安装包已排除所有 TypeScript 源码（`.ts`）和源映射文件（`.js.map`），只包含编译后的 JavaScript 代码（`dist/src` 目录）。Python 代码包含在 `rs-engine-bundle.tar` 和 `products-bundle.tar` 中。

### Q5: 如何在其他电脑上安装

1. 将 `RsAgent-0.0.11-win-x64.exe` 拷贝到目标电脑
2. 双击安装
3. 安装 Python 3.10+ 并安装依赖（`pip install fastmcp mcp aiohttp numpy`）
4. 如需要，设置 `PILOTDECK_CONDA_PYTHON` 环境变量
5. 配置 DeepSeek API Key
6. 启动 RsAgent

### Q6: 如何完全卸载

1. 通过"控制面板 → 程序和功能"卸载 RsAgent
2. 删除运行时数据目录：
   ```
   C:\Users\<用户名>\AppData\Roaming\RsAgent\
   C:\Users\<用户名>\.rsagent\
   ```

## 五、目录结构说明

安装后相关目录：

```
C:\Users\<用户名>\AppData\Local\RsAgent\          ← 应用程序（安装目录）
C:\Users\<用户name>\AppData\Roaming\RsAgent\runtime\  ← 运行时资源（首次启动解压）
  └── 0.0.11\
      ├── rsagent-main\        ← 主服务（Gateway，端口 18789）
      ├── rsagentui\            ← UI 服务（端口 18790）
      ├── rs-engine\            ← 遥感引擎
      └── products\             ← MCP 插件和技能
C:\Users\<用户名>\.rsagent\                         ← 用户数据
  ├── pilotdeck.yaml          ← 全局配置（模型、API Key）
  ├── desktop.server.log      ← 服务日志
  ├── plugins\                ← 插件目录
  └── skills\                 ← 技能目录
```
