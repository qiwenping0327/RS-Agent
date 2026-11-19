<h1 align="center">RsAgent</h1>

<p align="center">
  Task-oriented AI Agent productivity platform — an independent fork of PilotDeck with remote-sensing capabilities.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL_3.0-blue.svg?style=flat-square" alt="License"/></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Native-6366F1?style=flat-square" alt="MCP Native"/></a>
  <a href="https://github.com/OpenBMB/PilotDeck"><img src="https://img.shields.io/badge/Upstream-PilotDeck-FF6B35?style=flat-square" alt="Upstream"/></a>
</p>

<p align="center">
  <b>English</b> | <a href="./README.zh.md">简体中文</a>
  <br/>
  <a href="#-installation--quick-start">Quick Start</a> · <a href="#-key-highlights">Highlights</a> · <a href="#use-cases">Use Cases</a> · <a href="#-license">License</a>
</p>

---

> **RsAgent is an independent fork of [PilotDeck](https://github.com/OpenBMB/PilotDeck).**
> It is licensed under AGPL-3.0. The upstream project is jointly developed by
> Tsinghua University THUNLP, ModelBest, OpenBMB, and AI9Stars; this fork is
> maintained by RsAgent Contributors and is **not** endorsed by the upstream
> project or those organizations. See [NOTICE](NOTICE) and
> [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

---

## 💡 About RsAgent

**RsAgent** is a modified fork of [PilotDeck](https://github.com/OpenBMB/PilotDeck), an open-source agent operating system designed around the concept of "WorkSpace". The upstream project is jointly developed by Tsinghua University [THUNLP](https://nlp.csai.tsinghua.edu.cn/), [ModelBest](https://modelbest.cn/), [OpenBMB](https://www.openbmb.cn/), and [AI9Stars](https://github.com/AI9Stars). This fork keeps the WorkSpace-centered architecture and adds remote-sensing capabilities (rs-engine, open-earth-engine, and the rs-agent plugin) plus desktop packaging. It is maintained by RsAgent Contributors and is not endorsed by the upstream project.

A wave of excellent AI Agent harnesses has emerged in recent years, each with its own focus: **Claude Code / Cursor / Trae Solo** brought model reasoning deep into the programming IDE; **Claude Cowork** introduced the notion of project-level isolation to desktop-side knowledge work; **WorkBuddy** connected agents to IM ecosystems such as WeCom and Feishu so AI is one message away.

When we shift the lens from "one-shot programming" or "immediate Q&A" to **long-running, multi-project productivity work**, however, several questions remain open:

- When many projects run in parallel, can memory be **white-box and traceable**? When the AI gets something wrong, can you pinpoint which memory entry caused it and edit it directly — without starting a new chat from scratch?
- Can token cost be **tracked per task**, so that running agents in the background actually becomes economically viable?
- Can tasks of different difficulty **automatically be matched to different models**, instead of burning the flagship model on trivial calls?
- When you step away from the keyboard, can the work keep moving? Can the agent **proactively discover what's worth doing, report progress, and land results as files on disk**?

RsAgent is an incremental exploration around exactly these questions. It uses the WorkSpace as the fundamental unit — completely isolating files, memory and skills per project — and pairs it with three pillar capabilities: **White-box Memory**, **Smart Routing** and **Always-on**. The entire system natively supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) and behaves consistently across front-ends (Web / CLI / IM).

### ✨ Key Highlights

<table width="100%">
<tr>
<td width="50%" valign="top">

**WorkSpace-Level Isolation & Accretion**

Every project gets its own file system, memory store and skill set. Parallel work no longer interferes with itself, retrieval has a bounded scope, and skills accrete naturally as each task grows — no more global context pollution.

<p align="center">
  <img src="assets/workspace_en.gif" width="100%" alt="WorkSpace isolation demo"/>
</p>

</td>
<td width="50%" valign="top">

**Traceable White-box Memory**

Memory generation, extraction, storage and retrieval are visible end-to-end. When the AI mis-remembers, you can pinpoint and fix the offending entry. Built-in **Dream Mode** consolidates memory in idle windows, and supports one-click rollback.

<p align="center">
  <img src="assets/memory_en.gif" width="100%" alt="White-box memory demo"/>
</p>

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Smart Routing & Cost Optimization**

Task difficulty is auto-detected; complex calls go to flagship models (e.g. Claude 3.5 Sonnet / GPT-4o), simple ones drop to lighter models. Through on-device / cloud co-orchestration and precise matching, token spend shrinks dramatically without sacrificing quality.

<p align="center">
  <img src="assets/router.gif" width="100%" alt="Smart routing demo"/>
</p>

</td>
<td width="50%" valign="top">

**Always-on Background Execution**

RsAgent breaks the "you ask, it answers" loop: after you sign off, the agent keeps discovering candidate tasks, running long-horizon monitors, and finally lands deliverables as local files with a summary report waiting for you.

<p align="center">
  <img src="assets/awo_en.gif" width="100%" alt="Always-on execution demo"/>
</p>

</td>
</tr>
</table>

### 📊 Real-world Numbers

The three pillar capabilities have shown clear advantages in production-grade workflows:

#### 1. Smart Routing — ~70% cost savings on social-media workloads

In Xiaohongshu-style social-media operations, enabling Smart Routing automatically demotes simple polishing / layout tasks to a sub-agent (e.g. Sonnet 4.5) and only invokes Opus 4.5 at planning checkpoints:

<table width="100%">
<tr>
<th width="22%" align="left">Setup</th>
<th width="48%" align="left">Model configuration</th>
<th width="15%" align="left">Cost</th>
<th width="15%" align="left">Multiplier</th>
</tr>
<tr>
<td><b>Smart Routing ON</b></td>
<td>Opus 4.5 (main) + Sonnet 4.5 (sub)</td>
<td><b>$2.83</b></td>
<td><b>1.1×</b></td>
</tr>
<tr>
<td>Smart Routing OFF</td>
<td>All Opus 4.5 (main + sub)</td>
<td>$12.58</td>
<td>5.0×</td>
</tr>
<tr>
<td>Monolithic</td>
<td>Single Opus 4.5 long-react (estimated)</td>
<td>$12.20</td>
<td>4.8×</td>
</tr>
<tr>
<td colspan="4"><img width="840" height="1" alt=""/></td>
</tr>
</table>

#### 2. Smart Routing — 1/6 the cost while beating frontier models on hard tasks

The research team benchmarked 7 complex tasks (multilingual podcast push, multi-source data reports, domain-specific literature review, codebase architecture docs, etc.). The "strong main + light sub" routing setup matches or beats the frontier single-model setup at a fraction of the cost:

<table width="100%">
<tr>
<th width="70%" align="left">Setting</th>
<th width="15%" align="left">Score</th>
<th width="15%" align="left">Cost</th>
</tr>
<tr>
<td>MiniMax-M2.7 single-agent</td>
<td>37.1</td>
<td>$1.90</td>
</tr>
<tr>
<td>Claude Sonnet 4.6 single-agent</td>
<td>69.1</td>
<td>$18.36</td>
</tr>
<tr>
<td><b>Sonnet 4.6 (main) + MiniMax-M2.7 (sub)</b></td>
<td><b>70.6</b></td>
<td><b>$3.15</b></td>
</tr>
<tr>
<td colspan="3"><img width="840" height="1" alt=""/></td>
</tr>
</table>

#### 3. White-box Memory — layout & tone never bleed across projects

In black-box agents, mixing tasks in a shared context pool inevitably pollutes memory. RsAgent's WorkSpace-scoped white-box memory addresses this end-to-end:

<table width="100%">
<thead>
<tr>
  <th width="14%" align="left">Dimension</th>
  <th width="41%" align="left">Current AI Agents (black-box)</th>
  <th width="45%" align="left">RsAgent (white-box)</th>
</tr>
</thead>
<tbody>
<tr>
  <td><b>Visibility</b></td>
  <td>You can't see what the AI remembers, only what it outputs</td>
  <td>View every memory entry: what was stored, when, and which WorkSpace</td>
</tr>
<tr>
  <td><b>Control</b></td>
  <td>Once written, memory can't be edited or removed</td>
  <td>Edit / delete entries, pin critical decisions so they don't drift</td>
</tr>
<tr>
  <td><b>Traceability</b></td>
  <td>When it goes wrong, you can't find the root cause</td>
  <td>Generation → extraction → storage → retrieval, all auditable</td>
</tr>
<tr>
  <td><b>Isolation</b></td>
  <td>One shared pool — projects bleed into each other</td>
  <td>Scoped per WorkSpace; A's memory never reaches B</td>
</tr>
<tr>
  <td><b>Reversible</b></td>
  <td>After compression, the original is gone</td>
  <td>Dream-mode supports <b>one-click rollback</b> to the prior state</td>
</tr>
</tbody>
</table>

---

## 🖥️ UI & Demo

RsAgent ships an out-of-the-box Web UI with full WorkSpace management, white-box memory editing, and visualization of multi-agent collaboration.

### Use Cases

> All demos below are generated entirely by edge-side models via RsAgent's Smart Routing — no cloud-side frontier model required.

#### Work Document Generation

> *"Survey the Chinese LLM application market and turn it into a formal HTML white paper."*

<table width="100%">
<tr>
<td width="50%" align="center"><b>Process</b></td>
<td width="50%" align="center"><b>Result</b></td>
</tr>
<tr>
<td><img src="assets/en/ppt_en.gif" width="100%"/></td>
<td><img src="assets/result/ppt_result_en.gif" width="100%"/></td>
</tr>
</table>

#### Mini-Game Development

> *"Walk me through building an iOS AR mini-game Ball Finder in Vibe Coding mode."*

<table width="100%">
<tr>
<td width="50%" align="center"><b>Process</b></td>
<td width="50%" align="center"><b>Result</b></td>
</tr>
<tr>
<td><img src="assets/en/iosgame_en.gif" width="100%"/></td>
<td align="center"><img src="assets/result/ios_game_result.gif" width="60%"/></td>
</tr>
</table>

#### AI Engineering Platform Development

> *"Build a low-code embedding fine-tuning platform from scratch."*

<table width="100%">
<tr>
<td width="50%" align="center"><b>Process</b></td>
<td width="50%" align="center"><b>Result</b></td>
</tr>
<tr>
<td><img src="assets/en/modeltraining_en.gif" width="100%"/></td>
<td><img src="assets/result/modeltrainingresult_en.gif" width="100%"/></td>
</tr>
</table>

#### Audio-Video Editing & Social Media Operations

> *"Push this English podcast to a global audience in Chinese / Japanese / French / Korean / Spanish / Arabic."*

<table width="100%">
<tr>
<td width="50%" align="center"><b>Process</b></td>
<td width="50%" align="center"><b>Result (with audio)</b></td>
</tr>
<tr>
<td><img src="assets/en/podcast_en.gif" width="100%"/></td>
<td>

https://github.com/user-attachments/assets/a7245467-ee3c-4939-a055-c56576ac56d1

</td>
</tr>
</table>

---

## 📦 Installation & Quick Start

### Option A: Desktop app (recommended)

Download the latest RsAgent desktop build from the
[Releases page](https://github.com/qiwenping0327/RS-Agent/releases).

### Option B: From source (for developers)

**1. Clone and install dependencies**

> This repo uses [Git LFS](https://git-lfs.com/) for large media assets. Make sure `git lfs` is installed before cloning.
> If you don't need the demo videos/GIFs, add `GIT_LFS_SKIP_SMUDGE=1` before `git clone` to skip downloading them.

```bash
git clone https://github.com/qiwenping0327/RS-Agent.git
cd RS-Agent

npm install              # root deps (Gateway runtime)
cd ui && npm install     # UI deps
cd ..
```

> The server/CLI entry point is still named `pilotdeck` for compatibility with
> the upstream project. It is part of RsAgent, not the upstream distribution.

**Desktop build runtime binaries (not committed to Git)**

The desktop build needs `node.exe` and `bun.exe`, which are large binaries and
are intentionally excluded by `.gitignore`. Obtain them from the official
distributions or from the assets attached to this repository's
[Releases page](https://github.com/qiwenping0327/RS-Agent/releases), then
place them at:

```text
apps/desktop/resources/node-bin/node.exe   # Node.js 22.14.0 (Windows x64)
apps/desktop/resources/bun-bin/bun.exe     # Bun (Windows build)
```

Official sources:

- Node.js 22.14.0 Windows x64: <https://nodejs.org/dist/v22.14.0/win-x64/node.exe>
- Bun releases: <https://github.com/oven-sh/bun/releases>

The corresponding license texts are in `LICENSES/Node.js-LICENSE.txt` and
`LICENSES/Bun-LICENSE.md`.

**2. Configure a model provider**

RsAgent reads `~/.pilotdeck/pilotdeck.yaml` (the path is kept for compatibility with the upstream project). You can create it manually, let the bootstrap script generate one, **or just open the Web UI and configure providers visually in the settings panel.**
Supported protocols include OpenAI, Anthropic, DeepSeek, Qwen, Kimi, MiniMax and other OpenAI-compatible endpoints.

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

**3. Start the services**

```bash
cd ui && npm run dev     # dev mode (HMR), visit http://localhost:5173
# or
cd ui && npm run start   # production mode, visit http://localhost:3001
```

### Option C: Docker Compose

If Docker is installed, you can start RsAgent with:

```bash
docker compose up -d
```

---

## 🛠️ Extension Protocol

RsAgent inherits PilotDeck's open plugin architecture, with a strict boundary between the open-source core and plugin customization. Extending the system is a `plugin.json` away:

- **MCP Servers** — first-class integration with any Model Context Protocol server.
- **Tools & Skills** — register custom tools, or pull community skills via [ClawHub](https://www.npmjs.com/package/clawhub).
- **Lifecycle Hooks** — intercept `PreToolUse`, `UserPromptSubmit`, and other critical lifecycle events.
- **Custom Memory** — plug in your own memory store provider.

---

## 🤝 Contributing

Thanks to everyone who has contributed to the upstream PilotDeck project. New contributors are warmly welcome to this fork as well.

Workflow: **Fork → feature branch → PR**.

### Secret scanning hook

The repository ships a lightweight pre-commit hook that blocks common
`sk-`-style API keys, GitHub tokens, AWS access keys, and private keys:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit   # macOS / Linux
```

---

## 💬 Community

- For bugs and feature requests in this fork, please open an issue in
  [this repository](https://github.com/qiwenping0327/RS-Agent/issues).
  For issues that also affect the upstream project, please report them to
  [OpenBMB/PilotDeck](https://github.com/OpenBMB/PilotDeck/issues).
- Upstream community channels, website, and demo belong to the upstream
  project and are not operated by this fork. Please see
  [OpenBMB/PilotDeck](https://github.com/OpenBMB/PilotDeck).

---

## 🙏 Acknowledgements

We thank Agent OS pioneers such as OpenClaw, Claude Code, Codex, Cursor, and Hermes for their explorations that helped shape this field.

The upstream PilotDeck project builds upon the following outstanding open-source projects (this list is retained for attribution):

- [ClawXRouter](https://github.com/OpenBMB/ClawXRouter) — Intelligent model routing
- [ClawXMemory](https://github.com/OpenBMB/ClawXMemory) — Agent memory system
- [Claude Code UI](https://github.com/siteboon/claudecodeui) — Web UI reference
- [Claude Code Router](https://github.com/musistudio/claude-code-router) — Model routing reference
- [UltraRAG](https://github.com/OpenBMB/UltraRAG) — RAG framework
- [Anthropic Skills](https://github.com/anthropics/skills) — Agent skill framework and built-in skills (skill-creator)
- [Vercel Labs Skills](https://github.com/vercel-labs/skills) — find-skills skill
- [MiniMax-AI Skills](https://github.com/MiniMax-AI/skills) — minimax-pdf skill
- [frontend-slides](https://github.com/zarazhangrui/frontend-slides) — Create beautiful slides on the web using a coding agent's frontend skills
- [Karpathy Guidelines](https://x.com/karpathy/status/2015883857489522876) — LLM coding behavioral guidelines
- [Vite](https://github.com/vitejs/vite) — Frontend build tool
- [React](https://github.com/facebook/react) — UI framework
- [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss) — Utility-first CSS framework
- [shadcn/ui](https://github.com/shadcn-ui/ui) — Accessible component primitives for React

---

## 🏢 Upstream Project

RsAgent is based on PilotDeck. The upstream project is jointly developed by
Tsinghua University [THUNLP](https://nlp.csai.tsinghua.edu.cn/),
[ModelBest](https://modelbest.cn/), [OpenBMB](https://www.openbmb.cn/) and
[AI9Stars](https://github.com/AI9Stars). RsAgent Contributors are independent
of these organizations, and this fork is not endorsed by them.

- Upstream repository: [OpenBMB/PilotDeck](https://github.com/OpenBMB/PilotDeck)
- Upstream license: AGPL-3.0

---

## ⭐ Support the Upstream Project

If the underlying PilotDeck project has been helpful in your work or research,
please consider giving the [upstream repository](https://github.com/OpenBMB/PilotDeck)
a Star.

---

## 📝 Citation

The following citation refers to the **upstream PilotDeck project**, not to this
fork:

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

## 📦 Source Code for Binary Releases

Desktop installers and bundle archives are built from this repository. The
corresponding source for each binary release is the tagged commit listed on the
[Releases page](https://github.com/qiwenping0327/RS-Agent/releases).
If you received a binary without a source link, you can obtain the corresponding
source from <https://github.com/qiwenping0327/RS-Agent> at the same
version/tag. This satisfies the corresponding-source requirement of AGPL-3.0.

---

## 📄 License

RsAgent is a modified version of PilotDeck and is licensed under the
[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-only). See
[NOTICE](NOTICE) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for
attribution, the modification statement, and third-party licenses.
