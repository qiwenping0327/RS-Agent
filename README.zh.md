<h1 align="center">观境 · 遥感智能体（RS-Agent）</h1>

<p align="center">
  面向任务制的 AI Agent 生产力平台 —— 基于 PilotDeck 二次开发，并加入遥感能力。
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL_3.0-blue.svg?style=flat-square" alt="License"/></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Native-6366F1?style=flat-square" alt="MCP Native"/></a>
  <a href="https://github.com/OpenBMB/PilotDeck"><img src="https://img.shields.io/badge/上游-PilotDeck-FF6B35?style=flat-square" alt="上游项目"/></a>
</p>

<p align="center">
  <a href="./README.md">English</a> | <b>简体中文</b>
  <br/>
  <a href="#-安装与快速开始">快速开始</a> · <a href="#-核心亮点">核心亮点</a> · <a href="#使用场景">使用场景</a> · <a href="#-许可证">许可证</a>
</p>

---

> **观境 RS-Agent 是 [PilotDeck](https://github.com/OpenBMB/PilotDeck) 的独立二次开发分支。**
> 本项目遵循 AGPL-3.0。上游项目由清华大学 THUNLP 实验室、面壁智能、OpenBMB
> 与 AI9Stars 联合研发；本分支由 RsAgent Contributors 维护，**未获得**上游项目
> 或上述机构的背书。详见 [NOTICE](NOTICE) 与
> [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。

---

## 💡 关于观境 RS-Agent

**观境 RS-Agent** 是 [PilotDeck](https://github.com/OpenBMB/PilotDeck) 的二次开发版本。PilotDeck 是一个以「WorkSpace（工作舱）」为核心设计的开源智能体操作系统，由清华大学 [THUNLP](https://nlp.csai.tsinghua.edu.cn/) 实验室、[面壁智能](https://modelbest.cn/)、[OpenBMB](https://www.openbmb.cn/) 与 [AI9Stars](https://github.com/AI9Stars) 联合研发并开源。本分支保留其 WorkSpace 架构，并增加遥感能力（rs-engine、open-earth-engine、rs-agent 插件）与桌面端打包。本项目由 RsAgent Contributors 维护，未获得上游项目背书。

当前 AI Agent Harness 领域已涌现出一批优秀的代表成果，各有侧重：**Claude Code / Cursor / Trae Solo** 把模型的推理能力深度集成进了编程 IDE；**Claude Cowork** 引入了项目隔离的概念，把 Agent 带到了桌面端的知识工作场景；**WorkBuddy** 打通了 IM 生态，让 AI 在企微 / 飞书等通讯工具中触手可及。

然而，当我们把视角从"单次编程"或"即时问答"切换到**长周期、多项目并行的生产力创作**时，仍有一些尚未被很好回答的问题：

- 多项目并行时，记忆能否做到 **白盒可追溯**？AI 记错了，能否定位到哪条记忆出错、直接修改，而不必重开会话？
- Token 成本能否 **按任务分项追踪**？让后台常驻推进变得经济可行？
- 不同难度的任务，能否 **自动匹配不同模型**？而不是简单任务也跑最贵的旗舰模型？
- 人离开电脑后，活能否继续推进？Agent 能否 **主动发现值得做的事、汇报进展、把成果落地为文件**？

观境 RS-Agent 正是围绕这些问题做的增量探索。它以 WorkSpace 为基本单位，将文件、记忆、技能在项目级别完整隔离与沉淀，并配套提供 **白盒记忆**、**智能路由**、**Always-on** 三大能力，整套系统原生支持 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)，跨前端（Web / CLI / IM）行为一致。

### ✨ 核心亮点

<table width="100%">
<tr>
<td width="50%" valign="top">

**WorkSpace 级隔离与沉淀**

每个项目拥有独立的专属文件系统、记忆库与技能集。多任务并行互不干扰，检索空间有边界，技能随任务自动沉淀，告别全局上下文污染。

<p align="center">
  <img src="assets/workspace_en.gif" width="100%" alt="WorkSpace 级隔离与沉淀演示"/>
</p>

</td>
<td width="50%" valign="top">

**可追溯的白盒记忆**

记忆的生成、抽取、存储与使用全链路可见。AI 记错时可直接定位并手动修改。内置 **Dream 模式**，利用空闲时间自动归纳整理，并支持一键回滚。

<p align="center">
  <img src="assets/memory.gif" width="100%" alt="白盒记忆演示"/>
</p>

</td>
</tr>
<tr>
<td width="50%" valign="top">

**智能路由与成本优化**

内置任务难度识别，复杂任务调用强力模型（如 Claude 3.5 Sonnet / GPT-4o），简单任务降级至轻量模型。通过端云协同与精准匹配，大幅降低 Token 消耗。

<p align="center">
  <img src="assets/router.gif" width="100%" alt="智能路由演示"/>
</p>

</td>
<td width="50%" valign="top">

**Always-on 常驻执行**

突破"你问我答"的限制。用户离开后，Agent 仍能在后台主动发现潜在任务、执行长周期监控、并最终将成果落地为本地文件与摘要汇报。

<p align="center">
  <img src="assets/awo.gif" width="100%" alt="Always-on 常驻执行演示"/>
</p>

</td>
</tr>
</table>

### 📊 核心能力实测数据

观境 RS-Agent 的三大核心能力在实际生产环境中展现出了显著的优势：

#### 1. 智能路由：社媒场景节省 ～70% 成本

在小红书等社媒运营场景中，开启智能路由后，系统会自动将简单的文本润色、排版任务降级给子 Agent（如 Sonnet 4.5），仅在核心规划节点使用 Opus 4.5，实测成本大幅下降：

<table width="100%">
<tr>
<th width="22%" align="left">方案</th>
<th width="48%" align="left">模型编排</th>
<th width="15%" align="left">费用</th>
<th width="15%" align="left">倍率</th>
</tr>
<tr>
<td><b>开启省钱路由</b></td>
<td>主 Opus 4.5 + 子 Sonnet 4.5</td>
<td><b>$2.83</b></td>
<td><b>1.1×</b></td>
</tr>
<tr>
<td>不开省钱路由</td>
<td>全 Opus 4.5（主 + 子）</td>
<td>$12.58</td>
<td>5.0×</td>
</tr>
<tr>
<td>单体大模型</td>
<td>单体 Opus 4.5 长 react（预估）</td>
<td>$12.20</td>
<td>4.8×</td>
</tr>
<tr>
<td colspan="4"><img width="840" height="1" alt=""/></td>
</tr>
</table>

#### 2. 智能路由：复杂任务 1/6 成本超越顶级模型

研究团队在播客多语言推送、多源数据报告、领域论文综述、代码库架构文档等 7 个复杂任务上进行了对比测试。结果表明，采用"主强子弱"的路由编排，能以极低的成本达到最优效果：

<table width="100%">
<tr>
<th width="70%" align="left">配置</th>
<th width="15%" align="left">得分</th>
<th width="15%" align="left">成本</th>
</tr>
<tr>
<td>MiniMax-M2.7 单 Agent</td>
<td>37.1</td>
<td>$1.90</td>
</tr>
<tr>
<td>Claude Sonnet 4.6 单 Agent</td>
<td>69.1</td>
<td>$18.36</td>
</tr>
<tr>
<td><b>主 Sonnet 4.6 + 子 MiniMax-M2.7</b></td>
<td><b>70.6</b></td>
<td><b>$3.15</b></td>
</tr>
<tr>
<td colspan="3"><img width="840" height="1" alt=""/></td>
</tr>
</table>

#### 3. 白盒记忆：排版与文风不再"串台"

在传统的黑盒 Agent 中，多任务混居会导致记忆全局污染。观境 RS-Agent 通过 WorkSpace 实现了记忆的白盒化管理：

<table width="100%">
<thead>
<tr>
  <th width="14%" align="left">维度</th>
  <th width="41%" align="left">现有 AI Agent（黑盒）</th>
  <th width="45%" align="left">观境 RS-Agent（白盒）</th>
</tr>
</thead>
<tbody>
<tr>
  <td><b>可见性</b></td>
  <td>看不到 AI 记住了什么，只能看到最终输出</td>
  <td>随时查看记住了哪些内容、何时记录、属于哪个 WorkSpace</td>
</tr>
<tr>
  <td><b>可控性</b></td>
  <td>写入后无法修改、删除，只能等 AI 自己"想明白"</td>
  <td>手动改 / 删 / 标记关键节点，重要决策不丢失</td>
</tr>
<tr>
  <td><b>可追溯</b></td>
  <td>出错时无法定位根本原因</td>
  <td>生成 → 抽取 → 存储 → 使用，每个环节可查可改</td>
</tr>
<tr>
  <td><b>隔离性</b></td>
  <td>共享一个记忆池，跨项目互相污染</td>
  <td>按 WorkSpace 隔离，A 项目的记忆不会跑到 B 项目</td>
</tr>
<tr>
  <td><b>可回滚</b></td>
  <td>上下文压缩后无法查看原始内容</td>
  <td>Dream 整理后支持一键回滚到整理前状态，不怕"越整理越乱"</td>
</tr>
</tbody>
</table>

---

## 🖥️ 交互界面与演示

观境 RS-Agent 提供了开箱即用的 Web UI，支持完整的 WorkSpace 管理、白盒记忆编辑、以及多智能体协作过程的可视化。

### 使用场景

> 以下所有演示均由端侧模型通过观境 RS-Agent 智能路由完成生成——无需调用云端大模型。

#### 工作文档生成

> *"调研一下中国大模型应用市场，整理成一份正式的 HTML 白皮书"*

<table width="100%">
<tr>
<td width="50%" align="center"><b>执行过程</b></td>
<td width="50%" align="center"><b>最终成果</b></td>
</tr>
<tr>
<td><img src="assets/zh/ppt_zh.gif" width="100%"/></td>
<td><img src="assets/result/ppt_result_zh.gif" width="100%"/></td>
</tr>
</table>

#### 小游戏开发

> *"用 Vibe Coding 模式陪我做一款 iOS AR 小游戏《找球球》"*

<table width="100%">
<tr>
<td width="50%" align="center"><b>执行过程</b></td>
<td width="50%" align="center"><b>最终成果</b></td>
</tr>
<tr>
<td><img src="assets/zh/iosgame_zh.gif" width="100%"/></td>
<td align="center"><img src="assets/result/ios_game_result.gif" width="60%"/></td>
</tr>
</table>

#### AI 工程平台开发

> *"从零造一个 Embedding 低代码调优平台"*

<table width="100%">
<tr>
<td width="50%" align="center"><b>执行过程</b></td>
<td width="50%" align="center"><b>最终成果</b></td>
</tr>
<tr>
<td><img src="assets/zh/modeltraining_zh.gif" width="100%"/></td>
<td><img src="assets/result/modeltraining_result_zh.gif" width="100%"/></td>
</tr>
</table>

#### 音视频剪辑&自媒体运营

> *"把这期英文播客推送给中日法韩西阿六语全球受众"*

<table width="100%">
<tr>
<td width="50%" align="center"><b>执行过程</b></td>
<td width="50%" align="center"><b>最终成果（含音频）</b></td>
</tr>
<tr>
<td><img src="assets/zh/podcast_zh.gif" width="100%"/></td>
<td>

https://github.com/user-attachments/assets/a7245467-ee3c-4939-a055-c56576ac56d1

</td>
</tr>
</table>

---

## 📦 安装与快速开始

### 方式一：桌面端安装包 (推荐)

请从 [Releases 页面](https://github.com/qiwenping0327/RS-Agent/releases)
下载最新的观境 RS-Agent 桌面端安装包。

### 方式二：源码启动 (适合开发者)

**1. 克隆代码与安装依赖**

> 本仓库使用 [Git LFS](https://git-lfs.com/) 管理大型媒体文件。克隆前请确保已安装 `git lfs`。
> 如果不需要演示视频/GIF，可在 clone 前加上 `GIT_LFS_SKIP_SMUDGE=1` 跳过下载。

```bash
git clone https://github.com/qiwenping0327/RS-Agent.git
cd RS-Agent

npm install              # 安装根目录依赖 (Gateway 运行时)
cd ui && npm install     # 安装 UI 依赖
cd ..
```

> 服务端/CLI 入口名仍为 `pilotdeck`，这是为了兼容上游项目；它是观境 RS-Agent 的一部分，
> 不是上游发行版。

**桌面端构建所需的运行时二进制（不入库）**

桌面端构建需要 `node.exe` 与 `bun.exe`，它们体积较大，已通过 `.gitignore`
排除，不提交到 Git。请从官方发行版或本仓库
[Releases 页面](https://github.com/qiwenping0327/RS-Agent/releases)
的附件获取，并放到：

```text
apps/desktop/resources/node-bin/node.exe   # Node.js 22.14.0 (Windows x64)
apps/desktop/resources/bun-bin/bun.exe     # Bun (Windows 版本)
```

官方下载地址：

- Node.js 22.14.0 Windows x64：<https://nodejs.org/dist/v22.14.0/win-x64/node.exe>
- Bun Releases：<https://github.com/oven-sh/bun/releases>

对应许可证全文见 `LICENSES/Node.js-LICENSE.txt` 与 `LICENSES/Bun-LICENSE.md`。

**2. 配置模型 Provider**
观境 RS-Agent 依赖 `~/.pilotdeck/pilotdeck.yaml` 进行配置（该路径为兼容上游而保留）。您可以手动创建、运行启动脚本自动生成，**或者在启动 Web UI 后直接在设置界面中进行可视化配置**。
支持 OpenAI、Anthropic、DeepSeek、Qwen、Kimi、MiniMax 等多种协议。

```yaml
schemaVersion: 1
agent:
  model: deepseek/deepseek-v4-pro
model:
  providers:
    deepseek:
      protocol: openai
      url: https://api.deepseek.com/v1
      apiKey: sk-your-api-key
```

**3. 启动服务**

```bash
cd ui && npm run dev     # 开发模式 (HMR)，访问 http://localhost:5173
# 或
cd ui && npm run start   # 生产模式，访问 http://localhost:3001
```

### 方式三：Docker Compose

如果您已安装 Docker，也可以直接使用容器方式启动：

```bash
docker compose up -d
```

---

## 🛠️ 扩展与插件 (Extension Protocol)

观境 RS-Agent 继承自 PilotDeck 的开放插件架构，插件代码与开源核心严格隔离。开发者可以通过 `plugin.json` 轻松扩展系统能力：

- **MCP Servers**: 原生支持集成 Model Context Protocol 服务器。
- **Tools & Skills**: 注册自定义工具，或通过 [ClawHub](https://www.npmjs.com/package/clawhub) 引入社区 Skill。
- **Lifecycle Hooks**: 拦截 `PreToolUse`、`UserPromptSubmit` 等关键生命周期。
- **Custom Memory**: 允许接入自定义的记忆存储 Provider。

---

## 🤝 参与贡献

感谢所有为上游 PilotDeck 提交代码与反馈的开发者。本分支同样欢迎新的成员加入，共同完善观境 RS-Agent。

贡献流程：**Fork 本仓库 → 创建 Feature 分支 → 提交 PR**。

### 提交前密钥扫描钩子

仓库内置了一个轻量的 pre-commit 钩子，用于拦截常见的 `sk-` 形式 API Key、
GitHub Token、AWS Access Key 与私钥：

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit   # macOS / Linux
```

---

## 💬 联系我们

- 本分支的技术问题与功能请求，请提交到
  [本仓库 Issues](https://github.com/qiwenping0327/RS-Agent/issues)。
- 同时影响上游项目的问题，请提交到
  [OpenBMB/PilotDeck Issues](https://github.com/OpenBMB/PilotDeck/issues)。
- 上游项目的官网、Demo 与社群入口请访问
  [OpenBMB/PilotDeck](https://github.com/OpenBMB/PilotDeck)。这些入口属于上游项目，
  不代表观境 RS-Agent 本分支。

---

## 🙏 致谢

感谢 OpenClaw、Claude Code、Codex、Cursor、Hermes 等 Agent OS 先行者的探索，为这一领域的发展提供了重要启发。

上游 PilotDeck 的建设离不开以下优秀开源项目的支持（此列表用于致谢与来源说明）：

- [ClawXRouter](https://github.com/OpenBMB/ClawXRouter) — 智能模型路由
- [ClawXMemory](https://github.com/OpenBMB/ClawXMemory) — Agent 记忆系统
- [Claude Code UI](https://github.com/siteboon/claudecodeui) — Web UI 参考
- [Claude Code Router](https://github.com/musistudio/claude-code-router) — 模型路由参考
- [UltraRAG](https://github.com/OpenBMB/UltraRAG) — RAG 框架
- [Anthropic Skills](https://github.com/anthropics/skills) — Agent 技能框架和内置技能（skill-creator）
- [Vercel Labs Skills](https://github.com/vercel-labs/skills) — find-skills 技能
- [MiniMax-AI Skills](https://github.com/MiniMax-AI/skills) — minimax-pdf 技能
- [frontend-slides](https://github.com/zarazhangrui/frontend-slides) — 用编程 Agent 的前端能力创建精美网页幻灯片
- [Karpathy Guidelines](https://x.com/karpathy/status/2015883857489522876) — LLM 编码行为准则
- [Vite](https://github.com/vitejs/vite) — 前端构建工具
- [React](https://github.com/facebook/react) — UI 框架
- [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) — 原子化 CSS 框架
- [shadcn/ui](https://github.com/shadcn-ui/ui) — 可访问的 React 组件原语

---

## 🏢 上游项目

观境 RS-Agent 基于 PilotDeck。上游项目由清华大学
[THUNLP](https://nlp.csai.tsinghua.edu.cn/)、[面壁智能](https://modelbest.cn/)、
[OpenBMB](https://www.openbmb.cn/) 与 [AI9Stars](https://github.com/AI9Stars)
联合研发。RsAgent Contributors 与上述机构相互独立，本分支未获得其背书。

- 上游仓库：[OpenBMB/PilotDeck](https://github.com/OpenBMB/PilotDeck)
- 上游许可证：AGPL-3.0

---

## ⭐ 支持上游项目

如果底层的 PilotDeck 项目对您的工作或研究有帮助，请为
[上游仓库](https://github.com/OpenBMB/PilotDeck)点亮一颗 Star。

---

## 📝 引用

以下引用针对**上游 PilotDeck 项目**，不是对本分支的引用：

```bibtex
@misc{pilotdeck2026,
  author       = {PilotDeck Team},
  title        = {PilotDeck: A WorkSpace-Centric Open-Source Agent Operating System},
  howpublished = {\url{https://github.com/OpenBMB/PilotDeck}},
  year         = {2026},
  note         = {Accessed: 2026-05-29}
}
```

---

## 📦 二进制发行版的源码获取

桌面端安装包与 bundle 压缩包由本仓库构建。每个二进制发行版对应的源码，
就是 [Releases 页面](https://github.com/qiwenping0327/RS-Agent/releases)
中该版本所标注的 tag/commit。若您收到的二进制包没有附带源码链接，可在
<https://github.com/qiwenping0327/RS-Agent> 获取同一版本/tag 的源码。
这满足 AGPL-3.0 对"对应源码"的要求。

---

## 📄 许可证

观境 RS-Agent 是 PilotDeck 的二次开发版本，基于
[GNU Affero General Public License v3.0](LICENSE)（AGPL-3.0-only）开源。
署名、修改声明与第三方许可证见 [NOTICE](NOTICE) 与
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
