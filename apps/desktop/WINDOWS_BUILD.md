# RsAgent Windows 打包指南

> 在 Windows 上把 RsAgent 编译成可直接双击安装的 .exe 安装程序

---

## 一、前置准备（一次性）

### 1. 安装 Node.js

下载并安装 **Node.js v22.14.0**（与项目锁定的版本一致）：

- 官方下载：https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi
- 安装时勾选 **"Add to PATH"**
- 安装后打开 `cmd` 验证：

```bat
node --version
npm --version
```

### 2. 安装 Git for Windows

- 下载：https://git-scm.com/download/win
- 安装时选择 **"Git from the command line and also from 3rd-party software"**

### 3. 安装 Visual Studio Build Tools（编译 native 模块）

> `better-sqlite3` 等模块需要 C++ 编译器

- 下载 [Visual Studio Build Tools 2022](https://visualstudio.microsoft.com/zh-hans/downloads/)（勾选 **"使用 C++ 的桌面开发"** 工作负载）

### 4. 安装 Python（编译脚本依赖）

- 下载 Python 3.12：https://www.python.org/downloads/
- 安装时勾选 **"Add Python to PATH"**

### 5. 克隆代码

```bat
cd C:\projects
git clone https://github.com/qiwenping0327/RS-Agent.git
cd RS-Agent
```

---

## 二、配置 LLM API（首次运行需要）

应用首次启动会弹出 Onboarding 窗口，需要填入至少一个 LLM provider 的 `apiKey` / `baseUrl`。
- 配置保存到 `C:\Users\<你的用户名>\.rsagent\rsagent.yaml`

---

## 三、一键构建（推荐）

项目已经提供了完整脚本 [build-win.bat](scripts/build-win.bat)，在仓库根目录执行即可：

```bat
cd C:\projects\rs-agent
apps\desktop\scripts\build-win.bat
```

脚本会自动完成 10 个步骤：

| 步骤 | 内容 |
| --- | --- |
| 1 | `git pull` 拉取最新代码 |
| 2 | 安装根目录和 apps/desktop 的 npm 依赖 |
| 3 | 下载 Windows 版 Node.js v22.14.0 |
| 3b | 用 bundled Node 重新编译 `better-sqlite3` 等 native 模块 |
| 4 | 下载 Windows 版 Bun |
| 5 | 用 vite 构建 `ui/` |
| 6 | 用 tsc 构建 `src/context/memory/edgeclaw-memory-core` 和根 `src/` |
| 7 | 打包三个 tar：`rsagentui-bundle.tar` / `rsagent-main-bundle.tar` / `rsagent-memory-core-bundle.tar` |
| 8 | 生成 `dist\build-info.json`（版本号、git SHA、构建日期） |
| 9 | `npx tsc` 编译 Electron 主进程 TypeScript |
| 10 | `electron-builder --win --x64 --arm64` 产出安装包 |

### 常用参数

```bat
:: 已经装好依赖、只想重新打包
apps\desktop\scripts\build-win.bat --skip-install --skip-build

:: 只打 x64，跳过 arm64（CI 提速）
apps\desktop\scripts\build-win.bat --x64-only

:: 第一次跑全流程（最常用）
apps\desktop\scripts\build-win.bat
```

构建成功后，安装包出现在：

```
apps\desktop\dist-electron\
  ├─ RsAgent-0.0.11-win-x64.exe       # ← x86_64 安装程序
  └─ RsAgent-0.0.11-win-arm64.exe     # ← ARM64 安装程序（如启用）
```

---

## 四、手动构建（理解原理时使用）

```bat
:: 1. 安装依赖
cd C:\projects\rs-agent
npm install --ignore-scripts
cd apps\desktop
npm install
cd ..\..

:: 2. 准备 bundled 资源
mkdir apps\desktop\resources\node-bin
mkdir apps\desktop\resources\bun-bin

curl -fsSL -o apps\desktop\resources\node-bin\node-win-x64.zip ^
  https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip
tar xf apps\desktop\resources\node-bin\node-win-x64.zip ^
  -C apps\desktop\resources\node-bin ^
  --strip-components=1 node-v22.14.0-win-x64\node.exe
del apps\desktop\resources\node-bin\node-win-x64.zip

curl -fsSL -o apps\desktop\resources\bun-bin\bun-win-x64.zip ^
  https://github.com/oven-sh/bun/releases/download/bun-v1.3.10/bun-windows-x64.zip
tar xf apps\desktop\resources\bun-bin\bun-win-x64.zip ^
  -C apps\desktop\resources\bun-bin ^
  --strip-components=1 bun-windows-x64\bun.exe
del apps\desktop\resources\bun-bin\bun-win-x64.zip

:: 3. 编译 native 模块
set PATH=apps\desktop\resources\node-bin;%PATH%
node apps\desktop\resources\node-bin\node_modules\npm\bin\npm-cli.js rebuild better-sqlite3

:: 4. 构建 UI + main
cd ui
npx vite build
cd ..
cd src\context\memory\edgeclaw-memory-core
npx tsc -p tsconfig.json
cd ..\..\..\..
npx tsc -p tsconfig.json

:: 5. 打包三个 tar
cd ui
tar cf apps\desktop\resources\rsagentui-bundle.tar ^
  --exclude=node_modules/.cache ^
  --exclude=node_modules/.bin ^
  package.json server shared dist scripts node_modules
cd ..

tar cf apps\desktop\resources\rsagent-main-bundle.tar ^
  --exclude=apps --exclude=ui --exclude=old_ui ^
  --exclude=docs --exclude=tests --exclude=.git ^
  src dist\src scripts node_modules package.json tsconfig.json

cd src\context\memory\edgeclaw-memory-core
tar cf apps\desktop\resources\rsagent-memory-core-bundle.tar ^
  package.json lib ui-source
cd ..\..\..\..

:: 6. 生成 build-info.json
for /f "delims=" %i in ('git rev-parse --short HEAD') do set GIT_SHA=%i
for /f "delims=" %i in ('node -e "console.log(require('./apps/desktop/package.json').version)"') do set VERSION=%i
echo {"version":"%VERSION%","gitSha":"%GIT_SHA%","buildDate":"2026-06-24","mode":"manual"} > apps\desktop\dist\build-info.json

:: 7. 编译 Electron 主进程
cd apps\desktop
npx tsc

:: 8. electron-builder 打包
set CSC_IDENTITY_AUTO_DISCOVERY=false
npx electron-builder --win --x64 --arm64
```

> 说明：`node.exe`、`bun.exe` 及同类大体积运行时二进制已通过 `.gitignore`
> 排除，不提交到仓库；也可从本仓库 Releases 页面获取。对应许可证见
> `LICENSES\Node.js-LICENSE.txt` 与 `LICENSES\Bun-LICENSE.md`。

---

## 五、验证安装包

构建完成后执行 `apps/desktop/scripts/verify-installer.bat`：

```bat
apps\desktop\scripts\verify-installer.bat
```

它会自动检查：

1. `RsAgent Setup*.exe` 存在
2. `win-unpacked\RsAgent.exe` 主程序存在
3. `resources\app.asar` 资源就位
4. bundled `node.exe` / `bun.exe` 可执行
5. 三个 bundle tar 可解压
6. Gateway 进程能启动并响应 `/health`

---

## 六、安装与运行

### 安装

双击 `RsAgent-0.0.11-win-x64.exe`，按向导选择安装目录（默认 `C:\Users\<user>\AppData\Local\Programs\RsAgent`）。

> NSIS 配置（见 [electron-builder.yml](electron-builder.yml)）：`oneClick: false` + `allowToChangeInstallationDirectory: true` → 用户可以选择安装位置 + 创建桌面快捷方式 + 开始菜单快捷方式。

### 首次启动

1. 双击桌面 **RsAgent** 快捷方式
2. 弹出 Onboarding 窗口（如果没有 `~/.pilotdeck/pilotdeck.yaml`）
3. 填入 LLM provider 的 `apiKey` / `baseUrl`
4. 主程序启动 → 系统托盘出现 RsAgent 图标
5. 浏览器窗口加载 `http://127.0.0.1:18790/`

### 系统托盘操作

- **左键单击**：切换主窗口显示/隐藏
- **右键菜单**：
  - 显示主窗口
  - 在浏览器中打开 / 复制本机地址（端口动态变化时菜单自动刷新）
  - 检查更新（基于 `electron-updater`）
  - 显示服务日志 / 显示配置文件夹 / 显示崩溃报告
  - 退出 RsAgent

### 全局快捷键

- **Ctrl + Shift + P**：从任何应用快速唤起 / 隐藏主窗口
- macOS 上对应 **Cmd + Shift + P**

---

## 七、常见问题

### Q1: 构建报 "better-sqlite3 找不到 node-gyp"

A: 重新执行：
```bat
set PATH=apps\desktop\resources\node-bin;%PATH%
node "%ProgramFiles%\nodejs\node_modules\npm\bin\npm-cli.js" rebuild better-sqlite3
```

### Q2: 启动后白屏 / 端口被占用

A: 检查 `~/.rsagent/desktop.server.log`。常见原因：旧进程没退完 → 任务管理器结束所有 `RsAgent.exe` / `node.exe`。

### Q3: 提示 "无法验证发布者"

A: 默认未签名是正常的（用户说明中已要求排除 Windows 签名）。右键 .exe → 属性 → 勾选"取消锁定"。

### Q4: 想跳过 arm64 节省时间

A:
```bat
apps\desktop\scripts\build-win.bat --x64-only
```

### Q5: 重新构建前清理

A:
```bat
rmdir /s /q apps\desktop\dist
rmdir /s /q apps\desktop\dist-electron
rmdir /s /q dist
```

---

## 八、构建产物清单

| 路径 | 说明 |
| --- | --- |
| `apps/desktop/dist-electron/RsAgent-0.0.11-win-x64.exe` | x86_64 安装程序（~150MB） |
| `apps/desktop/dist-electron/RsAgent-0.0.11-win-arm64.exe` | ARM64 安装程序（仅当 build 时加 `--arm64`） |
| `apps/desktop/dist-electron/win-unpacked/` | 解包后的应用目录（可执行 `RsAgent.exe` 直接运行） |
| `apps/desktop/dist/build-info.json` | 版本号 + git SHA + 构建日期 |

---

## 九、不在本指南范围内

- **Windows 代码签名**：用户已要求排除
- **Linux 平台打包**：用户已要求排除
- **macOS 打包**：参考 [release.sh](scripts/release.sh)（仅 macOS 上运行）
- **自动更新到 GitHub Releases**：在 [electron-builder.yml](electron-builder.yml) 中已预留 `publish: github` 配置（当前为注释状态）；构建时如需跳过发布 `set CSC_IDENTITY_AUTO_DISCOVERY=false` 即可
