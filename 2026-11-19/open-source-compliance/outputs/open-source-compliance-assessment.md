# PilotDeck 二次开发项目开源合规评估与操作清单

- 评估对象：`d:\project\PilotDeck`（本地项目名 RsAgent，基于 OpenBMB/PilotDeck 二次开发）
- 评估日期：2026-11-19
- 评估性质：基于仓库实际文件的许可证合规评估，不构成法律意见
- 对比基准：上游 `https://github.com/OpenBMB/PilotDeck`，`main` 分支 commit `681ab48535f93da6833c81cb0ebc16c3cb606412`（2026-11-18）
- 评估方式：仓库文件清点 + 与上游逐文件哈希比对 + npm 依赖许可证扫描 + conda 环境元数据（`conda-meta/*.json`）许可证扫描 + 打包产物内容抽检
- 本次未修改仓库任何源码或许可证文件，仅新增本评估文档

---

## 一、执行摘要（先看结论）

### 1.1 一句话结论

**上游 PilotDeck 采用 AGPL-3.0；本仓库包含大量上游代码，属于 AGPL 衍生作品。开源整个项目本身是允许的，但必须整体继续使用 AGPL-3.0、保留上游许可与署名、显著声明修改、向用户提供完整对应源码；不能闭源分发，也不能自行改成商业专有许可。**

### 1.2 最关键的阻塞项（开源发布前必须处理）

| 级别 | 阻塞项 | 证据 | 不处理的后果 |
|---|---|---|---|
| P0 | README 仍宣称本项目由清华 THUNLP / ModelBest / OpenBMB / AI9Stars "jointly developed"，并沿用上游官网、Demo、社群二维码 | `README.md` 第 40、423 行；`README.zh.md` 同类表述 | 虚假署名 + 让人误以为获得上游/高校背书，商标与不正当竞争风险 |
| P0 | 应用内唯一"开源"链接原指向不存在的 OpenBMB 仓库（已修复为 `https://github.com/qiwenping0327/RS-Agent`） | `ui/src/components/auth/view/AuthScreenLayout.tsx` 第 48 行附近 | 违反 AGPL 第 13 条"网络交互须提供源码"的实质要求，且误导用户 |
| P0 | 源码中硬编码 6 处 API Key（博查、DeepSeek、图像模型等） | `open-earth-engine/open_earth_engine/knowledge/knowledge_mcp_server.py:445`、`open-earth-engine/oea_service.py:1474,1569`、`fix-runtime.bat:94`、`gpt-image-2-integration-changes.md:324`、`SYNC_GUIDE.md:72` | 密钥泄露、被滥用产生费用；即使许可证合规也不能这样开源 |
| P0 | 无 `NOTICE` / `THIRD-PARTY-NOTICES`；`apps/desktop` 声明 `AGPL-3.0-or-later`，与上游 `AGPL-3.0` 不一致；root/ui/offline-package 无 `license` 字段 | `package.json`、`ui/package.json`、`apps/desktop/package.json`、`offline-package/package.json` | 许可证声明自相矛盾，分发时缺少必要声明，审计无法通过 |
| P1 | 分发物包含未附许可证的 Node/Bun 运行时；`dependencies/` 下 290MB conda 环境含 GPL-2.0-only、GPL-3.0-only、LGPL、MPL 组件 | `apps/desktop/resources/node-bin/node.exe`、`bun-bin/bun.exe`（目录内仅有 exe）；conda `conda-meta` 扫描结果见第五章 | 分发 GPL/LGPL 二进制却未附许可证/源码提供方式，构成许可证违约 |
| P1 | 仓库内直接存放大量构建产物与二进制包（`dist/`、`apps/desktop/dist-*`、`*.tar`、`dependencies/`、`offline-package/`） | 文件清点：`node_modules` 106,006 个文件、`offline-package` 3,776 个、`dependencies` 约 2.75GB（含多份重复打包） | 一旦整目录上传，等于分发目标代码，触发 AGPL 第 6 条"对应源码"义务；同时仓库体积失控 |
| P1 | `offline-package/` 是项目旧快照，`package.json` 名称仍为 `pilotdeck`，README 仍是上游 README，且没有 `LICENSE` 文件 | `offline-package/package.json`、`offline-package/README.md`、`offline-package` 下无 LICENSE | 形成"无许可证的二次分发副本"，且再次复制上游品牌与署名 |

### 1.3 建议的总体路线

1. **许可策略定为 AGPL-3.0-only**：保留根 `LICENSE` 原文不动，所有子包统一 `"license": "AGPL-3.0-only"`。
2. **保留上游署名，改写本项目署名**：新增 `NOTICE`，README 增加"Upstream / Based on"章节，删除"联合开发"等虚假表述。
3. **补齐第三方声明**：新增 `THIRD-PARTY-NOTICES.md` 与 `LICENSES/` 目录，覆盖 npm 依赖、Node/Bun/Electron、conda 环境（若分发）、技能、字体。
4. **发布物与源码分离**：Git 仓库只放源码与声明文件；安装包、bundle tar、conda 环境走 Releases，并附"对应源码"链接。
5. **改品牌与来源说明**：产品保留 RsAgent 名称可以，但必须明确"RsAgent is a modified fork of PilotDeck, not endorsed by the PilotDeck team"；停止使用上游 Logo、社群二维码、官网作为本项目信息。
6. **清理密钥与内部资料**：撤销并轮换全部泄露 Key，移除内部文档、测试数据、构建产物。

---

## 二、评估方法与证据边界

### 2.1 实际执行的检查

| 检查项 | 方法 | 结果位置 |
|---|---|---|
| 上游许可证 | GitHub API 仓库元数据 + 上游 `LICENSE` 与本地 `LICENSE` 哈希比对 | 本文件 3.1 |
| 衍生关系 | 将本地 `src/`、`ui/src/`、`apps/desktop/src/`、`scripts/`、`skills/`、`products/` 与上游同目录逐文件 MD5 比对 | 本文件 3.2 |
| 本地许可声明 | 读取根目录及子包 `package.json`、根 `LICENSE`、README | 本文件第四章 |
| npm 依赖许可证 | 遍历 `node_modules/.pnpm`、`ui/node_modules`、`apps/desktop/node_modules` 中所有 `package.json` 的 `license` 字段，并核对缺失字段包的 `LICENSE` 文件 | 本文件 5.1 |
| Python/conda 依赖 | 从 `dependencies/rs-agent-conda-env.tar.gz` 解出 `conda-meta/*.json`，统计 153 个 conda 包的 `license` 字段 | 本文件 5.2 |
| 打包产物 | 列出 `apps/desktop/resources/*.tar` 顶层与许可证文件数量；检查 `.js.map`/`.ts`；检查 `dist-build/win-unpacked` | 本文件第六章 |
| 静态资源与技能 | 本地 `assets/` 与上游逐文件哈希比对；检查 `skills/*/LICENSE` 与 SKILL.md 元数据 | 本文件 5.3、5.4 |
| 敏感信息 | 对非 `node_modules` 文本文件正则扫描 `sk-[A-Za-z0-9]{20,}` | 本文件第八章 |

### 2.2 证据边界（必须说明）

- 本地目录**不是 Git 仓库**（无 `.git`），无法取得真实的 fork 起点、提交历史与逐行修改记录。因此：
  - "与上游相同"是**确定证据**；
  - "被修改"只能说明"与 2026-11-18 的上游 main 不同"，其中可能包含上游后续演进造成的差异，不能全部算作本地修改；
  - 无法给出"精确的本地修改文件清单"，只能给出统计与抽样。
- 本评估未对每个文件做法律意义上的"实质性相似"判断，只做工程层面的来源识别。
- 未核验上游是否与任何主体签署过单独商业许可；仓库内没有此类文本，**不能推定存在**。
- 未核验 `PilotDeck`、`RsAgent` 是否已注册商标；这需要商标检索与法务判断。

---

## 三、上游许可证结论与权利义务

### 3.1 已确认：上游是 AGPL-3.0

| 证据 | 内容 |
|---|---|
| GitHub API `repos/OpenBMB/PilotDeck` | `license.spdx_id = "AGPL-3.0"`，`license.name = "GNU Affero General Public License v3.0"` |
| 上游 `LICENSE` | 标准 GNU AGPL v3 全文，无附加条款、无项目版权行 |
| 本地 `LICENSE` | 与上游 `LICENSE` **字节完全一致**（MD5 均为 `11DA06444AFC8233C93D92F2FF286607`） |
| 上游与本地 README | 均标注 `License-AGPL_3.0`，License 章节写 "GNU Affero General Public License v3.0" |
| 上游 `package.json` | **没有** `license` 字段，也没有 `"or later"` 表述 |
| 上游仓库文本检索 | `*.md` 中未发现 commercial / trademark / dual-license / CLA 等附加条款 |

**结论：上游授予的是 AGPL-3.0（按 only 理解最稳妥），没有发现任何"允许闭源商用"的附加许可。**

> 说明：AGPL 正文的 "How to Apply" 示例里有 "or any later version"，那是 FSF 给的模板文字，不是上游项目的授权声明。上游 README 明确写 v3.0，且 GitHub 识别为 `AGPL-3.0` 而非 `AGPL-3.0-or-later`。因此本地写成 `AGPL-3.0-or-later` 属于**单方面扩大授权**，应改为 `AGPL-3.0-only`。

### 3.2 已确认：本仓库是 AGPL 衍生作品

与上游 `main`（commit `681ab48`）逐文件 MD5 比对结果：

| 目录 | 上游文件数 | 本地文件数 | 完全相同 | 不同 | 仅本地有 | 仅上游有 |
|---|---:|---:|---:|---:|---:|---:|
| `src/` | 684 | 517 | **199** | 312 | 6 | 173 |
| `ui/src/` | 811 | 282 | **58** | 131 | 93 | 622 |
| `apps/desktop/src/` | 34 | 11 | 0 | 2 | 9 | 32 |
| `scripts/` | 33 | 6 | 0 | 1 | 5 | 32 |
| `skills/` | 95 | 52 | **25** | 4 | 23 | 66 |
| `products/` | 6 | 15 | 4 | 2 | 9 | 0 |

（统计已排除 `node_modules`、`__pycache__`、`dist` 等生成目录。）

**结论：`src/` 至少有 199 个文件与上游逐字节相同，`ui/src/` 至少 58 个，`skills/` 至少 25 个；根 `LICENSE` 完全一致。这不是"参考思路"，而是直接包含上游代码，构成 AGPL 下的"基于该程序的作品"（work based on the Program）。**

因此：

- 整个组合作品（包括本地新增的 `rs-engine/`、`open-earth-engine/`、`products/`、`ui/` 修改等）在对外分发时，必须整体按 AGPL-3.0 授权；
- 不能只给上游部分附 AGPL、却把本地部分声明为专有；
- 不能把编译后的 bundle/asar 当作"独立程序"规避源码义务——它们与上游代码紧密结合，属于同一作品。

### 3.3 AGPL-3.0 允许与不允许的边界（已确认，基于许可证正文）

| 使用场景 | 是否允许 | 必须满足的条件 |
|---|---|---|
| 自己内部使用、不对外分发 | 允许 | 无源码公开义务（AGPL §2） |
| 开源发布修改版（源码形式） | 允许 | 保留版权与许可声明；显著声明"已修改"及日期；整体 AGPL；附完整 LICENSE（§4、§5） |
| 销售软件、安装包、U 盘等（目标代码形式） | 允许，可收费 | 必须同时提供"对应源码"（Corresponding Source），或许可证 §6 认可的书面要约/网络下载方式 |
| 作为 SaaS / 网络服务对外提供 | 允许 | 必须向所有远程交互用户**免费提供对应源码**的获取方式（§13）；这是 AGPL 与 GPL 的核心差异 |
| 闭源分发、专有许可再授权 | **不允许** | 除非取得上游版权人的单独许可（仓库内无此许可） |
| 改成 MIT/Apache/商业许可证 | **不允许** | 同上；本地新增部分可另行授权，但组合作品整体仍受 AGPL 约束 |
| 使用 `PilotDeck` 名称、Logo 做产品品牌 | **不能仅凭 AGPL 获得** | AGPL 不授予商标权；需商标检索与法务判断，通常只允许"说明来源"的合理使用 |
| 声称获得 OpenBMB/清华/ModelBest 背书 | **不允许** | 无授权依据，且与事实不符 |

关于"商用"的准确表述：

- **允许商用**：可以卖软件、卖部署、卖支持、卖托管服务；
- **但不允许"商用 + 闭源"**：只要对外分发或对外提供网络服务，衍生作品就必须以 AGPL 提供源码；
- **不能双许可**：除非上游版权人另行授权，否则你不能给客户一个"商业闭源许可证"来替代 AGPL。

### 3.4 上游是否提供商业授权

- 已检查上游仓库的 README、README.zh、LICENSE、package.json、docs（`*.md` 全量检索），**未发现任何 commercial license / 商业授权 / 联系方式**。
- 结论：**「需要用户/法务确认」**。如果业务上确实需要闭源或专有许可，必须直接联系 OpenBMB / PilotDeck 团队取得书面授权；不能从仓库内容推定存在。

---

## 四、当前仓库自身的许可状态

### 4.1 已有文件

| 文件 | 现状 | 评价 |
|---|---|---|
| `LICENSE` | AGPL-3.0 全文，与上游一致 | ✅ 正确，应保留不动 |
| `README.md` / `README.zh.md` | 上游 README 的改写版；仍大量保留上游品牌、官网、社群信息；声称"jointly developed by THUNLP/ModelBest/OpenBMB/AI9Stars" | ❌ 虚假署名、来源说明缺失、修改声明缺失 |
| `NOTICE` | 不存在 | ❌ 缺失 |
| `THIRD-PARTY-NOTICES*` | 不存在 | ❌ 缺失 |
| `COPYING` | 不存在 | 可不需要（LICENSE 已足够） |
| `skills/frontend-slides/LICENSE` | MIT（Copyright 2025 Zara Zhang） | ✅ 保留 |
| `skills/skill-creator/LICENSE.txt` | Apache-2.0 | ✅ 保留 |
| `skills/karpathy-guidelines/SKILL.md` | frontmatter 写 `license: MIT`，但无 LICENSE 全文 | ⚠️ 需补全文 |
| `skills/find-skills/` | 仅 `SKILL.md`，无 LICENSE | ⚠️ 需核实来源许可 |
| `skills/minimax-pdf/` | 本地新增，无 LICENSE；上游 README 将其归功于 MiniMax-AI Skills | ⚠️ 需核实来源许可 |
| `skills/doc-craft/`、`skills/rs-cartography/` | 无 LICENSE | 需确认是否为自研；若是自研，随项目 AGPL 即可 |
| `products/rs-agent/plugins/rs-agent/plugin.json` | 无 license 字段 | 作为项目一部分按 AGPL 即可，但建议补字段 |

### 4.2 `package.json` 许可字段

| 文件 | `name` | `license` | 问题 |
|---|---|---|---|
| 根 `package.json` | `rs-agent` | **缺失** | 应补 `AGPL-3.0-only` |
| `ui/package.json` | `rs-agent-ui` | **缺失** | 应补 |
| `apps/desktop/package.json` | `@rsagent/desktop` | `AGPL-3.0-or-later` | ❌ 与上游 only 冲突，应改 `AGPL-3.0-only` |
| `offline-package/package.json` | **`pilotdeck`** | **缺失** | ❌ 名称仍是上游名；应改名/加许可/或删除该目录 |
| `src/context/memory/edgeclaw-memory-core/package.json` | `edgeclaw-memory-core` | **缺失** | 应补 |
| `offline-package/src/context/memory/edgeclaw-memory-core/package.json` | 同上 | **缺失** | 同上 |

补充证据：

- `apps/desktop/electron-builder.yml` 第 3 行：`copyright: "Copyright © 2026 RsAgent Contributors. AGPL-3.0-or-later."`
- `apps/desktop/src/main.ts` 第 307 行有同样的 `AGPL-3.0-or-later` 文案
- `apps/desktop/package.json` 第 7 行：`"license": "AGPL-3.0-or-later"`

这些都应统一为 `AGPL-3.0-only`，并补上上游版权声明。

### 4.3 `offline-package/` 的特殊问题

- 它是本项目的一个旧快照（`src` 与当前 `src` 有差异，但结构相同），`package.json` 名称是 `pilotdeck`，README 是上游 README。
- 目录内**没有 LICENSE 文件**，README 里的 `href="LICENSE"` 是坏链接。
- 如果把它作为"离线安装包"对外分发，等于发布一个**没有许可证、且冒用上游署名**的衍生副本，风险很高。

**建议：不要把 `offline-package/` 放进开源仓库。** 如确需保留，改名、补 LICENSE/NOTICE、重写 README，并明确它与主仓库的版本对应关系。

### 4.4 README 的具体问题

| 位置 | 现状 | 应改为 |
|---|---|---|
| 第 40 行（`README.md`） | "**RsAgent** is ... jointly developed and open-sourced by Tsinghua University THUNLP, ModelBest, OpenBMB, and AI9Stars." | "RsAgent is an independent fork of PilotDeck. The upstream PilotDeck project is developed by ...; this fork is maintained by RsAgent Contributors and is not endorsed by the upstream project." |
| 第 423 行 | "PilotDeck is jointly developed by ..." | 移入 "Upstream" 章节，并明确这是上游事实，不是本项目 |
| 顶部徽章 | 上游官网、Demo、GitHub Stars、Discord/飞书/微信社群 | 删除或改为本项目自己的链接；上游信息放 "Upstream" 章节 |
| 第 445 行 License | 只写 "licensed under AGPL v3.0" | 增加 "This project is a modified version of PilotDeck... see NOTICE and THIRD-PARTY-NOTICES.md" |
| 文末 Citation | 仍是 PilotDeck 论文引用 | 保留为"上游引用"，不要让人误以为引用的是本项目 |

---

## 五、第三方代码与资源许可情况

### 5.1 npm 依赖（已扫描生产与开发依赖）

扫描范围：`node_modules/.pnpm`、`ui/node_modules`、`apps/desktop/node_modules` 下所有 `package.json`。许可证分布（按包名去重）：

| 许可证 | 包数量 |
|---|---:|
| MIT | 778 |
| ISC | 67 |
| Apache-2.0 | 33 |
| BSD-3-Clause | 22 |
| BSD-2-Clause | 12 |
| BlueOak-1.0.0 | 7 |
| CC0-1.0 / MIT-0 / 0BSD | 5 |
| **AGPL-3.0-or-later** | **1**（`mupdf`） |
| **LGPL-3.0-or-later** | **1**（`@img/sharp-libvips-linux-x64`） |
| **Apache-2.0 AND LGPL-3.0-or-later** | **1**（`@img/sharp-win32-x64`） |
| **MPL-2.0** | **1**（`web-push`） |
| **OFL-1.1** | **1**（`@fontsource-variable/inter`） |
| **CC-BY-4.0** | **1**（`caniuse-lite`，仅开发依赖） |
| `(MIT OR GPL-3.0-or-later)` | 1（`jszip`，可选 MIT） |

需要重点处理的依赖：

| 包 | 版本 | 许可证 | 影响与动作 |
|---|---|---|---|
| `mupdf` | 1.27.0 | AGPL-3.0-or-later | 与项目 AGPL 兼容✅；但它是**任何闭源/专有发布的硬约束**。必须随分发物附 MuPDF 的 AGPL 声明与源码获取方式（MuPDF 官方仓库/本项目源码中含该依赖）。若未来想改许可证，必须先替换它。 |
| `@img/sharp-win32-x64` | 0.34.5 | Apache-2.0 AND LGPL-3.0-or-later | 含 libvips 原生库。附 LGPL-3.0 全文与 libvips 源码获取方式；说明其为动态加载、可替换。 |
| `@img/sharp-libvips-linux-x64` | 1.2.4 | LGPL-3.0-or-later | 同上；Linux 发布物尤其要注意。 |
| `web-push` | 3.6.7 | MPL-2.0 | 附 MPL-2.0 全文；如修改其源文件，需公开被修改文件。 |
| `@fontsource-variable/inter` | 5.2.8 | OFL-1.1 | 附 SIL OFL 1.1 全文；如修改字体文件，不得使用保留字体名 "Inter"。 |
| `jszip` | 3.10.1 | MIT OR GPL-3.0-or-later | 选择 MIT 即可，记录选择。 |
| `caniuse-lite` | 0.1.30001793 | CC-BY-4.0 | 仅构建期使用；若把其数据打包进产品，需保留署名。 |
| `busboy` / `streamsearch` / `spawn-command` | 1.6.0 / 1.1.0 / 0.2.2 | `package.json` 无 license 字段，但包内**有 LICENSE 文件**（MIT/ISC） | 保留包内 LICENSE 文件，不要删除；在 THIRD-PARTY 中列出。 |
| `edgeclaw-memory-core` | 0.0.0 | 本地私有包，无 license | 属于本项目代码，按 AGPL 授权并补字段。 |

> 说明：扫描结果中出现的 `baz`、`beep-boop`、`false_main`、`invalid_main`、`browser_field`、`rxjs/ajax` 等是 npm 包内部测试夹具或子路径 `package.json`，不是真实依赖，可忽略。

**结论（已确认）：npm 依赖中没有发现 AGPL 不兼容的强 copyleft 许可证；`mupdf` 本身就是 AGPL，进一步锁死项目的 AGPL 属性。没有发现非商业（Non-Commercial）条款。**

### 5.2 conda 环境（`dependencies/rs-agent-conda-env.tar.gz`）

该包约 290MB，解出 `conda-meta/*.json` 后共 **153 个 conda 包**。许可证分布：

| 许可证 | 包数 |
|---|---:|
| MIT | 50 |
| BSD-3-Clause | 39 |
| BSD-2-Clause | 11 |
| Apache-2.0 | 8 |
| GPL-3.0-only WITH GCC-exception-3.1 | 6 |
| LGPL-2.1-or-later | 3 |
| Zlib | 3 |
| GPL-2.0-only OR FTL | 3 |
| GPL-3.0-only | 2 |
| LGPL-2.1-only | 2 |
| PSF-2.0 | 2 |
| ISC | 2 |
| MPL-1.1 | 1 |
| 其他（HPND、IJG、TCL、blessing、curl、zlib-acknowledgement、LicenseRef-Qhull 等） | 各 1 |
| 无 license 字段 | 1（`_libgcc_mutex`） |

**含 GPL/LGPL/MPL 的具体组件（已确认，来自 conda-meta）：**

| 包 | 版本 | 许可证 |
|---|---|---|
| `libnsl` | 2.0.0 | **GPL-2.0-only** |
| `ld_impl_linux-64` | 2.44 | **GPL-3.0-only** |
| `readline` | 8.3 | **GPL-3.0-only** |
| `libgcc` / `libgcc-ng` / `libgfortran` / `libgfortran5` / `libstdcxx` / `libstdcxx-ng` | 15.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `geos` | 3.10.6 | **LGPL-2.1-only** |
| `libiconv` | 1.18 | **LGPL-2.1-only** |
| `libglib` | 2.86.0 | LGPL-2.1-or-later |
| `cairo` | 1.18.4 | LGPL-2.1-or-later or MPL-1.1 |
| `fribidi` | 1.0.16 | LGPL-2.1-or-later |
| `keyutils` | 1.6.3 | LGPL-2.1-or-later |
| `xz` | 5.8.2 | LGPL-2.1-or-later and GPL-2.0-or-later and 0BSD |
| `graphite2` | 1.3.15 | LGPL-2.0-or-later |
| `freexl` | 2.0.0 | **MPL-1.1** |
| `libspatialite` | 5.1.0 | MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later |
| `freetype` / `libfreetype` / `libfreetype6` | 2.14.3 | GPL-2.0-only OR FTL（可选 FTL） |

**关键判断：**

- 这个 conda 环境是 Linux 二进制发行物，里面确实包含 **GPL-2.0-only / GPL-3.0-only** 组件；
- 它们与 Node 应用是"聚合（aggregate）"关系，不必然导致整个应用被 GPL 化，但**分发这些二进制本身必须遵守它们各自的许可证**：附许可证全文、提供对应源码（或书面的源码提供要约）；
- **GPL-2.0-only（`libnsl`）与 AGPL-3.0 不兼容**：不能宣称"这个 conda 环境整体是 AGPL"，只能按组件分别声明；如果要把它们与 AGPL 代码合并成单一作品，会有冲突。
- **结论：如果 `dependencies/` 随开源仓库或离线包一起分发，这是 P1 级合规缺口；最省事的做法是不要把 conda 环境放进源码仓库，而是作为独立二进制依赖发布，并附 `THIRD-PARTY-NOTICES` 与各组件源码链接（conda-forge feedstock / 上游项目）。**

> 说明：`rs-agent-deps-20260621_221506.tar.gz`、`rs-agent-full-deps.tar.gz`、`full-deps/` 是同一环境的重复打包（目录合计约 2.75GB），同样适用上述结论。

### 5.3 随包分发的运行时

| 运行时 | 位置 | 现状 | 缺失 |
|---|---|---|---|
| Node.js | `apps/desktop/resources/node-bin/node.exe`（79.5MB） | 目录内**只有 exe，没有 LICENSE** | 需附 Node.js LICENSE（Node 22.12.0 的 LICENSE 在 `dependencies/full-deps/node-runtime-20260621_221506.tar.gz` 的 `22.12.0/LICENSE`，已确认存在） |
| Bun | `apps/desktop/resources/bun-bin/bun.exe`（14.8MB） | 目录内**只有 exe，没有 LICENSE** | 需从 Bun 官方发行版取得 `LICENSE.md` 与第三方声明；Bun 自身 MIT，但二进制内含 JavaScriptCore 等组件（LGPL 系），不能只写 MIT |
| Electron | `apps/desktop/dist-build/win-unpacked/` | 已包含 `LICENSE.electron.txt`、`LICENSES.chromium.html` | ✅ 已有；确保安装包安装后这些文件仍在安装目录 |
| Chromium | 同上 | `LICENSES.chromium.html` 14.4MB | ✅ 已有 |
| pnpm（Node runtime 内） | `dependencies/full-deps/node-runtime-...tar.gz` | 含 `22.12.0/lib/node_modules/pnpm/LICENSE` | 若分发该 runtime，保留 |

**结论（已确认）：`node-bin` / `bun-bin` 是明确的许可证缺失项，属于 P1。**

### 5.4 技能（skills）与插件

| 技能 | 来源/许可证据 | 状态 |
|---|---|---|
| `frontend-slides` | `skills/frontend-slides/LICENSE`，MIT，Copyright 2025 Zara Zhang | ✅ 完整 |
| `skill-creator` | `skills/skill-creator/LICENSE.txt`，Apache-2.0 | ✅ 完整 |
| `karpathy-guidelines` | `SKILL.md` frontmatter `license: MIT`，正文注明 derived from Andrej Karpathy | ⚠️ 缺 MIT 全文与版权人信息 |
| `find-skills` | 上游 README 归功于 Vercel Labs Skills；本地仅有 `SKILL.md`，无 LICENSE | ⚠️ 需核实上游仓库许可证并补全文 |
| `minimax-pdf` | 上游 README 归功于 MiniMax-AI Skills；本地是新增目录，无 LICENSE | ⚠️ 需核实来源与许可；若无法确认，建议移除 |
| `doc-craft` | 无来源标注，无 LICENSE | 需确认是否自研；自研则随项目 AGPL |
| `rs-cartography` | 无来源标注，无 LICENSE | 同上 |
| `pilotdeck-skills-migration` | 名称暗示与上游技能迁移有关 | 需确认是否复制上游内容 |

**结论：`find-skills`、`minimax-pdf` 的再分发许可目前无法从仓库内确认，属于「需要用户/法务确认」；在确认前不要随开源版本发布。**

### 5.5 静态资源、字体、图片

- 本地 `assets/` 与上游 `assets/` 比对：**3 个文件完全相同，39 个不同，0 个本地独有**。说明 banner、演示 GIF、社群二维码等基本都源自上游（部分被替换/重制）。
- `assets/community/qr-discord.png`、`qr-feishu.png`、`qr-wechat.png`、`assets/banner.png`、`assets/*.gif` 属于上游品牌/社群素材：
  - 作为 AGPL 项目的一部分，可以在保留署名的情况下分发；
  - 但**不能用作本项目自己的品牌标识**，也不应让用户误以为这是上游官方社群。
- `ui/public/logo.svg`、`logo-128.png`、`logo-256.png`、`favicon.*`：需确认是自研还是上游素材；如来自上游，按上游素材处理并去掉商标性使用。
- 字体：`@fontsource-variable/inter` 为 OFL-1.1，需在 `THIRD-PARTY-NOTICES.md` 与 `LICENSES/` 中附 OFL 全文。
- `manual-images/*.svg`：本地自绘（未在上游出现），可随项目 AGPL。
- `data/`：包含测试影像、`.npy`、`.db`、`.docx` 等内部/运行数据，**不是软件源码**，不应进入开源仓库。

### 5.6 模型权重与模型相关资源

- 全仓库扫描 `*.onnx`、`*.pt`、`*.pth`、`*.safetensors`、`*.gguf`、`*.ckpt`、`*.bin`：**未发现模型权重文件**（仅 Electron 的 `snapshot_blob.bin`、`v8_context_snapshot.bin`，属于运行时快照，不是模型）。
- 但 `rs-engine` 与 `products/rs-agent` 的说明中多次提到 SAM2、MSCN、RemoteCLIP、YOLOv8、U-Net、BIT 等模型；当前仓库没有权重，**如果未来随包分发权重，需要单独核查每个模型的许可证**（例如 YOLOv8 为 AGPL-3.0，SAM2 为 Apache-2.0，RemoteCLIP 等需逐个确认）。
- 结论：**当前无模型权重分发，暂不构成许可问题；但属于未来发布的风险点。**

---

## 六、打包产物与分发义务

### 6.1 实际打包配置

`apps/desktop/electron-builder.yml` 的 `extraResources` 会把以下内容放进安装包：

```
resources/node-bin/            → node-bin/
resources/bun-bin/             → bun-bin/
resources/rsagentui-bundle.tar
resources/rsagent-main-bundle.tar
resources/rsagent-memory-core-bundle.tar
resources/rs-engine-bundle.tar
resources/products-bundle.tar
resources/open-earth-engine-bundle.tar
```

`files` 还会打包 `dist/**/*`、`onboarding/**/*`、`splash/**/*`、`assets/**/*`、`node_modules/**/*`、`package.json`。

### 6.2 bundle 内容抽检

| bundle | 大小 | 顶层 | 许可证文件数 | `.js.map` | 纯 `.ts` |
|---|---:|---|---:|---:|---:|
| `rsagent-main-bundle.tar` | 105.7MB | `dist/`、`node_modules/`、`package.json`、`scripts/` | 209 | 0 | 0 |
| `rsagentui-bundle.tar` | 212.6MB | `dist/`、`node_modules/`、`package.json`、`scripts/`、`server/`、`shared/` | 551 | 0 | 0 |
| `rsagent-memory-core-bundle.tar` | 0.7MB | `lib/`、`package.json`、`ui-source/` | 0 | 0 | 0 |
| `rs-engine-bundle.tar` | 0.5MB | `rs_engine/`、`data/`、`requirements.txt` 等 | 0 | 0 | 0 |
| `products-bundle.tar` | <0.1MB | `_example/`、`rs-agent/` | 0 | 0 | 0 |
| `open-earth-engine-bundle.tar` | 0.3MB | `open_earth_engine/`、`tests/`、`__pycache__/` | 0 | 0 | 0 |

结论：

- bundle 内 npm 依赖自带 LICENSE 文件（209 / 551 个），这是好事；
- 但**没有统一的 NOTICE / THIRD-PARTY 声明**，用户拿到安装包后无法一眼看到"这是 AGPL 作品、源码在哪里、包含哪些第三方组件"；
- `rsagent-memory-core`、`rs-engine`、`products`、`open-earth-engine` 是本地/上游自研代码，bundle 内没有 license 文件，需要由根目录声明覆盖；
- bundle 内未见 `.js.map` 和纯 `.ts`（符合"保护源码"的构建约束），但这也意味着**安装包是纯目标代码，必须依赖外部源码提供**。

### 6.3 `app.asar` 与安装目录

- `apps/desktop/dist-build/win-unpacked/resources/app.asar` 约 10.5MB，包含 Electron 主进程 `dist/`、`node_modules/`、`package.json` 等；
- `win-unpacked` 还包含 `LICENSE.electron.txt` 与 `LICENSES.chromium.html`（✅ Electron/Chromium 声明已有）；
- **没有** `LICENSE`（AGPL 全文）、`NOTICE`、`THIRD-PARTY-NOTICES.md`。

**AGPL 义务判断：**

- 安装包/bundle/asar 属于"目标代码形式"分发，触发 AGPL §6：必须提供"对应源码"；
- 如果源码在公开仓库，且安装包内/下载页明确给出**对应版本的源码地址（tag/commit）**，可以满足 §6(d)；
- 如果提供 SaaS/网络服务（Dockerfile `EXPOSE 3001`，可公网部署），还触发 §13：必须向远程用户提供源码获取方式；
- **仅写"代码在 GitHub"不够**：要写清楚"哪个版本/哪个 tag 对应哪个安装包"，并保证长期可访问。

### 6.4 仓库内的构建产物

当前仓库中存在：

- `dist/`（977 个文件，含 8 个 `.js.map`，位于 `dist/scripts/` 与 `dist/tests/`）；
- `apps/desktop/dist/`、`dist-build/`、`dist-new/`、`dist-release/`、`build-staging/`；
- `apps/desktop/resources/*.tar`（含 140.8MB / 280.6MB 的旧包与 `.tar.gz`）；
- `dependencies/`（约 2.75GB，含 conda 环境与 node_modules 快照，且存在多份重复打包）；
- `offline-package/`（3,776 个文件）；
- 根目录 `rs-agent-offline-20260621_221147.tar.gz`（15MB）。

`.gitignore` 已忽略 `node_modules/`、`dist`、`apps/desktop/resources/*.tar`，但**没有忽略** `dependencies/`、`offline-package/`、`dist-build/`、`*.tar.gz` 等。如果通过"上传整个文件夹"而不是 `git push` 发布，这些都会进入公开仓库。

**建议：发布前做一次"干净导出"，只保留源码、声明文件、构建脚本与必要配置；所有二进制/依赖/数据/内部文档走 Releases 或内部存储。**

---

## 七、结论分类

### 7.1 已确认（有仓库内直接证据）

1. 上游 PilotDeck 许可证为 **AGPL-3.0**；本地 `LICENSE` 与上游字节一致。
2. 本仓库包含上游代码，属于 **AGPL 衍生作品**（`src/` 199 个文件完全相同，`ui/src/` 58 个，`skills/` 25 个）。
3. 开源整个项目**允许**；闭源分发/专有再许可**不允许**（除非上游单独授权）；SaaS 必须提供源码。
4. 本地许可声明存在冲突：`apps/desktop` 写 `AGPL-3.0-or-later`，与上游 only 不一致；root/ui/offline-package 无 `license` 字段。
5. 仓库**没有** `NOTICE` / `THIRD-PARTY-NOTICES`；只有 `skills/frontend-slides/LICENSE`、`skills/skill-creator/LICENSE.txt` 两个第三方许可证全文。
6. `node-bin/node.exe`、`bun-bin/bun.exe` **没有随附许可证**。
7. `dependencies/` 下 conda 环境包含 **GPL-2.0-only、GPL-3.0-only、LGPL-2.1、MPL-1.1** 组件（`libnsl`、`readline`、`ld_impl_linux-64`、`geos`、`libglib`、`freexl` 等）。
8. npm 依赖中有 `mupdf`（AGPL-3.0-or-later）、`sharp`/libvips（LGPL-3.0-or-later）、`web-push`（MPL-2.0）、Inter 字体（OFL-1.1）。
9. 源码中存在 **6 处硬编码 API Key**。
10. README 的"联合开发"表述与事实不符；应用内源码链接指向 404 仓库。
11. 当前仓库**没有模型权重文件**。
12. `offline-package/` 无 LICENSE、名称为 `pilotdeck`、README 为上游版本。

### 7.2 需要用户确认 / 法务判断

| 事项 | 为什么无法从仓库判断 | 建议动作 |
|---|---|---|
| 上游版权人的准确署名写法 | 上游 `LICENSE` 没有项目版权行；README 只写 "PilotDeck Team"、"OpenBMB"、"THUNLP/ModelBest/AI9Stars" | 在 `NOTICE` 中使用 "Copyright (c) 2026 The PilotDeck Authors (OpenBMB and contributors)"，并请法务确认；或直接联系上游确认 |
| 上游是否提供商业/闭源授权 | 仓库内无任何 commercial license 文本 | 如业务需要闭源，必须书面联系 OpenBMB/PilotDeck 团队 |
| `PilotDeck` / `RsAgent` 商标状态与使用边界 | 需要商标检索；AGPL 不授予商标权 | 产品名与 Logo 做商标检索；对外只用"based on PilotDeck"的事实性描述，不使用上游 Logo/社群作为本项目官方信息 |
| 本地 UI 是否复制了 `claudecodeui` 等第三方代码 | 上游 README 仅写 "Web UI reference"；本地 `ui/src` 与上游有 93 个本地独有文件，无法逐一判断来源 | 对 `ui/src` 做一次来源审计；若确有复制，保留其 MIT 等许可证与版权声明 |
| `find-skills`、`minimax-pdf` 的再分发许可 | 仓库内无许可证文件；上游 README 只给出处 | 到对应上游仓库确认 LICENSE；确认前从开源版本移除或替换 |
| `doc-craft`、`rs-cartography` 是否完全自研 | 无来源标注 | 确认作者与贡献来源；自研则随项目 AGPL |
| conda 环境是否会对外分发 | 仓库内有 290MB 包，但安装包 `extraResources` 未包含它 | 明确发布渠道；若分发，按组件附 GPL/LGPL/MPL 许可证与源码提供方式 |
| 是否提供公网 SaaS | `Dockerfile` 暴露 3001，但实际部署方式未知 | 若提供公网服务，按 AGPL §13 在 UI/页脚提供源码链接 |
| 未来是否分发模型权重 | 当前无权重文件 | 发布前逐模型核查许可证（YOLOv8 为 AGPL，SAM2 为 Apache-2.0 等） |
| 上游素材（banner/GIF/二维码）的版权归属 | 上游仓库包含这些文件，但未单独声明 | 保守做法：保留上游署名；停止将社群二维码作为本项目官方入口 |

---

## 八、可执行操作清单

> 以下动作按优先级排序。标记 ✅ 的是"必须做"，标记 ⚠️ 的是"确认后再做"。

### 8.1 P0：开源前必须完成

#### 1. 保留 `LICENSE`，不要改

- 根 `LICENSE` 与上游一致，保留原文；
- 不要把它替换成 MIT/Apache，也不要在文件里追加"or later"。

#### 2. 新增 `NOTICE`

建议内容（中文项目可中英双语）：

```text
RsAgent
Copyright (c) 2026 RsAgent Contributors

This product is a modified version of PilotDeck
(https://github.com/OpenBMB/PilotDeck), which is licensed under the
GNU Affero General Public License, version 3 (AGPL-3.0).

Upstream copyright:
Copyright (c) 2026 The PilotDeck Authors (OpenBMB and contributors).
See the upstream repository for the full list of contributors.

This project is not endorsed by, affiliated with, or sponsored by the
PilotDeck project, OpenBMB, Tsinghua University, ModelBest, or AI9Stars.

Modifications began on [YYYY-MM-DD]. A summary of major modifications is
provided in MODIFICATIONS.md and in the project README.

The full source code for this version is available at:
[本项目仓库 URL，固定到 tag/commit]

Third-party components and their licenses are listed in
THIRD-PARTY-NOTICES.md and the LICENSES/ directory.
```

> ⚠️ 上游版权行的准确写法需要法务确认；如果无法确认，至少保留 "The PilotDeck Authors" 与上游仓库 URL。

#### 3. 新增 `THIRD-PARTY-NOTICES.md`

至少包含以下章节：

```markdown
# Third-Party Notices

## 1. Upstream project
- PilotDeck — https://github.com/OpenBMB/PilotDeck — AGPL-3.0
- 本项目修改说明见 NOTICE / MODIFICATIONS.md

## 2. Bundled runtimes
- Node.js 22.x — MIT — 附 LICENSES/Node.js-LICENSE.txt
- Bun — MIT + 其二进制内含组件的许可证 — 附 LICENSES/Bun-LICENSE.md 与官方 third-party notices
- Electron / Chromium — MIT / BSD-style — 安装目录已含 LICENSE.electron.txt、LICENSES.chromium.html

## 3. npm dependencies
（列出所有非 MIT/ISC/Apache/BSD 的依赖，或附自动生成的完整清单）
- mupdf 1.27.0 — AGPL-3.0-or-later
- @img/sharp-win32-x64 0.34.5 — Apache-2.0 AND LGPL-3.0-or-later
- @img/sharp-libvips-linux-x64 1.2.4 — LGPL-3.0-or-later
- web-push 3.6.7 — MPL-2.0
- @fontsource-variable/inter 5.2.8 — OFL-1.1
- jszip 3.10.1 — MIT (selected from MIT OR GPL-3.0-or-later)
- caniuse-lite — CC-BY-4.0 (build-time data)

## 4. Python / conda environment (if distributed)
- conda-forge packages, 153 packages; GPL/LGPL/MPL components listed below:
  - libnsl 2.0.0 — GPL-2.0-only
  - readline 8.3 — GPL-3.0-only
  - ld_impl_linux-64 2.44 — GPL-3.0-only
  - geos 3.10.6 — LGPL-2.1-only
  - libglib 2.86.0 — LGPL-2.1-or-later
  - freexl 2.0.0 — MPL-1.1
  - ...（完整清单）
- Source availability: [conda-forge feedstock / 上游项目链接]

## 5. Skills
- frontend-slides — MIT — Copyright (c) 2025 Zara Zhang
- skill-creator — Apache-2.0
- karpathy-guidelines — MIT — derived from Andrej Karpathy's observations
- find-skills — [待确认]
- minimax-pdf — [待确认]

## 6. Assets and fonts
- Inter font — SIL OFL 1.1
- Upstream PilotDeck demo assets — see upstream repository
```

#### 4. 新增 `LICENSES/` 目录

至少放入：

- `AGPL-3.0.txt`（可直接复制根 `LICENSE`）
- `Apache-2.0.txt`（skill-creator）
- `MIT-frontend-slides.txt`
- `MIT-karpathy-guidelines.txt`
- `OFL-1.1.txt`（Inter 字体）
- `LGPL-3.0.txt`（libvips/sharp）
- `MPL-2.0.txt`（web-push）
- `Node.js-LICENSE.txt`（可从 Node 22.12.0 发行包取得）
- `Bun-LICENSE.md` + `Bun-THIRD-PARTY-NOTICES`（从 Bun 发行版取得）
- 若分发 conda 环境：`GPL-2.0.txt`、`GPL-3.0.txt`、`LGPL-2.1.txt`、`MPL-1.1.txt` 及完整组件清单

#### 5. 统一 `package.json` 许可字段

| 文件 | 修改 |
|---|---|
| 根 `package.json` | 增加 `"license": "AGPL-3.0-only"`；建议增加 `"repository"`、`"homepage"` |
| `ui/package.json` | 增加 `"license": "AGPL-3.0-only"` |
| `apps/desktop/package.json` | `"AGPL-3.0-or-later"` → `"AGPL-3.0-only"` |
| `apps/desktop/electron-builder.yml` | copyright 文案改为 `AGPL-3.0-only`，并补上游署名 |
| `apps/desktop/src/main.ts` | 第 307 行同步修改 |
| `src/context/memory/edgeclaw-memory-core/package.json` | 增加 `"license": "AGPL-3.0-only"` |
| `offline-package/package.json` | 若保留：改名、加 license；若删除：见 8.3 |

#### 6. 改写 README（这是"修改声明"的核心位置）

建议结构：

```markdown
# RsAgent

> RsAgent is a modified fork of [PilotDeck](https://github.com/OpenBMB/PilotDeck).
> It is licensed under AGPL-3.0. See NOTICE and THIRD-PARTY-NOTICES.md.
> This fork is maintained by RsAgent Contributors and is not endorsed by
> the PilotDeck project, OpenBMB, Tsinghua University, ModelBest, or AI9Stars.

## About this fork
RsAgent adds remote-sensing capabilities (rs-engine, open-earth-engine,
rs-agent plugin) on top of PilotDeck. Modifications began on [date].

## Upstream
PilotDeck is developed by ... (upstream facts, with links).
Upstream license: AGPL-3.0.

## License
This project is licensed under AGPL-3.0. The full text is in LICENSE.
Corresponding source for released binaries: [URL/tag].
```

必须删除/修正：

- "jointly developed and open-sourced by Tsinghua .../ModelBest/OpenBMB/AI9Stars" 用于描述 RsAgent 的句子；
- 上游官网、Demo、Discord/飞书/微信二维码作为本项目官方入口；
- 上游 Citation 段落要么删除，要么明确标注 "Citation for the upstream project"。

#### 7. 修复应用内源码链接

- 文件：`ui/src/components/auth/view/AuthScreenLayout.tsx`（第 48 行附近）
- 原状态：`href` 指向一个不存在的 OpenBMB 仓库（404）；已修复为 `https://github.com/qiwenping0327/RS-Agent`
- 改为：本项目的真实仓库 URL；若尚未建仓，先指向项目主页/文档中的源码说明
- 建议同时在设置/关于页面增加 "Source code (AGPL-3.0)" 链接，满足 AGPL §13

#### 8. 清理密钥

| 文件 | 行 | 处理 |
|---|---|---|
| `open-earth-engine/open_earth_engine/knowledge/knowledge_mcp_server.py` | 445 | 删除默认值，改为必须从环境变量读取；撤销该 Key |
| `open-earth-engine/oea_service.py` | 1474、1569 | 同上 |
| `fix-runtime.bat` | 94 | 删除硬编码 Key |
| `gpt-image-2-integration-changes.md` | 324 | 删除或脱敏 |
| `SYNC_GUIDE.md` | 72 | 删除或脱敏 |

> 这些 Key 已经出现在本地文件中，即使删除文本也应视为已泄露，**必须到对应平台撤销/轮换**。

### 8.2 P1：发布质量与合规声明

1. **新增 `MODIFICATIONS.md`**：列出主要修改模块、日期、作者/维护者，满足 AGPL §5(a) 的"显著声明修改"要求。
   - 可包含：`src/` 中新增的远程感知模块、`ui/` 的界面改造、`rs-engine/`、`open-earth-engine/`、`products/rs-agent`、打包脚本等。
2. **在源文件头部加修改声明（可选但更稳妥）**：对明显修改过的上游文件，加一行：
   ```text
   Modified by RsAgent Contributors on 2026-xx-xx. See NOTICE.
   ```
   不必给所有文件加，但核心被改文件建议加。
3. **补 Node/Bun 许可证**：在 `apps/desktop/resources/node-bin/`、`bun-bin/` 放 `LICENSE`；并确保 `extraResources` 一并打包。
4. **生成完整的 npm 依赖清单**：建议用 `pnpm licenses list --prod` 或 `npx license-checker --production --json` 生成，作为 `THIRD-PARTY-NOTICES.md` 的附录。
5. **处理 `offline-package/`**：优先删除；若必须保留，补 LICENSE/NOTICE、改包名、重写 README，并明确版本对应关系。
6. **处理 `dependencies/`**：不要放进公开 Git 仓库；作为独立二进制依赖发布时，附 conda 组件许可证与源码链接。
7. **移除构建产物**：`dist/`、`apps/desktop/dist-*`、`*.tar`、`*.tar.gz`、`build-staging/`、`offline-package/`、`dependencies/`、`data/`、`temp/`、`workspace/`、`.pilotdeck/`、内部 `.docx`/`.md`。
8. **补充 `.gitignore`**：加入 `dependencies/`、`offline-package/`、`dist-build/`、`dist-new/`、`dist-release/`、`build-staging/`、`*.tar.gz`、`data/`、`temp/`、`.pilotdeck/`。
9. **处理 `dist/` 中 8 个 `.js.map`**：位于 `dist/scripts/` 与 `dist/tests/`；发布前删除或确认不进入发布物（源码保护与体积）。
10. **统一品牌素材**：确认 `ui/public/logo*`、`assets/banner.png`、社群二维码的来源；上游素材保留署名，产品 Logo 使用自研版本。

### 8.3 P2：发布流程与长期合规

1. **建立发布 checklist**：每次发版前检查
   - `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`、`LICENSES/` 是否随包；
   - 安装包下载页是否给出对应源码的 tag/commit；
   - Docker 镜像/在线服务是否在 UI 或文档中提供源码链接；
   - 新增依赖是否引入新的 copyleft/非商业许可证。
2. **CI 加许可证扫描**：在 CI 中运行 `pnpm licenses list` 或 `license-checker`，对 `GPL-2.0-only`、`AGPL`、`SSPL`、`BUSL`、`Non-Commercial` 等关键字做告警。
3. **SaaS 场景**：若对外提供 `http://host:3001` 服务，在登录页/页脚/关于页提供 "Source code" 链接，满足 AGPL §13；链接应指向与线上版本对应的 tag/commit。
4. **商标与命名**：
   - 产品名、Logo、域名、应用商店名称做商标检索；
   - 对外文案统一使用 "RsAgent, a fork of PilotDeck" 这类事实性描述；
   - 不使用 "Official"、"Powered by OpenBMB"、"Tsinghua" 等暗示背书的表述；
   - 不使用上游 Logo、社群二维码作为本项目官方入口。
5. **未来模型权重**：若分发 YOLOv8（AGPL）、SAM2（Apache-2.0）等权重，逐个记录许可证，并放入 `THIRD-PARTY-NOTICES.md`。
6. **贡献者许可**：如果希望接受外部贡献，建议加 `CONTRIBUTING.md`，明确贡献按 AGPL-3.0 授权（可选 DCO/CLA）；不要引入与 AGPL 冲突的贡献条款。

---

## 九、发布前检查清单（可直接勾选）

### 许可与声明

- [ ] 根 `LICENSE` 保持 AGPL-3.0 原文
- [ ] 新增 `NOTICE`，含上游署名、修改声明、非背书声明、源码地址
- [ ] 新增 `THIRD-PARTY-NOTICES.md`，覆盖 npm / 运行时 / conda / 技能 / 字体 / 素材
- [ ] 新增 `LICENSES/`，含 AGPL、Apache-2.0、MIT、OFL、LGPL、MPL 等全文
- [ ] 所有 `package.json` 使用 `AGPL-3.0-only`（root、ui、desktop、memory-core、offline-package）
- [ ] `electron-builder.yml` 与 `main.ts` 的 copyright 文案同步
- [ ] `offline-package` 已删除，或已补齐许可与来源说明

### 品牌与来源

- [ ] README 删除"联合开发"等虚假署名
- [ ] README 增加 "Upstream / Based on PilotDeck" 章节
- [ ] 删除/替换上游官网、Demo、社群二维码作为本项目信息
- [ ] 修复 `AuthScreenLayout.tsx` 的 404 源码链接
- [ ] UI/关于页提供 "Source code (AGPL-3.0)" 链接
- [ ] 产品名/Logo 已做商标检索；无 "Official/OpenBMB/Tsinghua" 暗示

### 分发物

- [ ] `node-bin/node.exe`、`bun-bin/bun.exe` 旁附 LICENSE
- [ ] 安装包内包含 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`、`LICENSES/`
- [ ] 安装包下载页给出对应源码 tag/commit
- [ ] 若分发 conda 环境：附 GPL/LGPL/MPL 许可证与源码提供方式
- [ ] 若提供 SaaS：UI/页脚提供源码链接
- [ ] bundle/asar 中无 `.js.map`、无纯 `.ts` 源码（或已确认可公开）
- [ ] 发布物与源码版本一一对应

### 仓库卫生

- [ ] 移除 `dependencies/`、`offline-package/`、`dist/`、`dist-*`、`*.tar`、`*.tar.gz`
- [ ] 移除 `data/`、`temp/`、`workspace/`、`.pilotdeck/`、内部文档与测试数据
- [ ] `.gitignore` 覆盖上述目录
- [ ] 撤销并轮换所有已泄露 API Key
- [ ] 扫描确认无其他密钥、证书、内部地址

---

## 十、附录：关键证据位置

### 10.1 许可证与声明

| 文件 | 说明 |
|---|---|
| `d:\project\PilotDeck\LICENSE` | AGPL-3.0，与上游 MD5 一致 |
| `d:\project\PilotDeck\README.md` 第 40、423、445 行 | 联合开发表述、上游署名、License 章节 |
| `d:\project\PilotDeck\README.zh.md` | 同上（中文版） |
| `d:\project\PilotDeck\package.json` | 无 license 字段 |
| `d:\project\PilotDeck\ui\package.json` | 无 license 字段 |
| `d:\project\PilotDeck\apps\desktop\package.json` 第 7 行 | `AGPL-3.0-or-later` |
| `d:\project\PilotDeck\apps\desktop\electron-builder.yml` 第 3 行 | copyright 文案 |
| `d:\project\PilotDeck\apps\desktop\src\main.ts` 第 307 行 | copyright 文案 |
| `d:\project\PilotDeck\offline-package\package.json` | `name: pilotdeck`，无 license |
| `d:\project\PilotDeck\offline-package\README.md` | 上游 README，无 LICENSE 文件 |
| `d:\project\PilotDeck\src\context\memory\edgeclaw-memory-core\package.json` | 无 license 字段 |

### 10.2 第三方许可证

| 文件/目录 | 说明 |
|---|---|
| `skills/frontend-slides/LICENSE` | MIT |
| `skills/skill-creator/LICENSE.txt` | Apache-2.0 |
| `skills/karpathy-guidelines/SKILL.md` | frontmatter `license: MIT` |
| `node_modules/.pnpm/mupdf@1.27.0/.../package.json` | AGPL-3.0-or-later |
| `node_modules/.pnpm/@img+sharp-win32-x64@0.34.5/.../package.json` | Apache-2.0 AND LGPL-3.0-or-later |
| `node_modules/.pnpm/web-push@3.6.7/.../package.json` | MPL-2.0 |
| `node_modules/.pnpm/@fontsource-variable+inter@5.2.8/.../package.json` | OFL-1.1 |
| `apps/desktop/resources/node-bin/` | 仅 `node.exe`，无 LICENSE |
| `apps/desktop/resources/bun-bin/` | 仅 `bun.exe`，无 LICENSE |
| `apps/desktop/dist-build/win-unpacked/LICENSE.electron.txt` | Electron 许可（已有） |
| `apps/desktop/dist-build/win-unpacked/LICENSES.chromium.html` | Chromium 许可（已有） |

### 10.3 conda 环境（若分发需处理）

| 组件 | 许可证 |
|---|---|
| `libnsl` 2.0.0 | GPL-2.0-only |
| `readline` 8.3 | GPL-3.0-only |
| `ld_impl_linux-64` 2.44 | GPL-3.0-only |
| `libgcc` / `libstdcxx` / `libgfortran` 15.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `geos` 3.10.6 | LGPL-2.1-only |
| `libiconv` 1.18 | LGPL-2.1-only |
| `libglib` 2.86.0 | LGPL-2.1-or-later |
| `cairo` 1.18.4 | LGPL-2.1-or-later or MPL-1.1 |
| `freexl` 2.0.0 | MPL-1.1 |
| `libspatialite` 5.1.0 | MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later |

### 10.4 敏感信息（已脱敏记录）

> 本节不保留任何完整 Key 或可用于还原的片段。完整值已从仓库中的源码、脚本、
> 文档、测试、构建产物、日志与缓存中移除或脱敏；维护者仍需到对应平台撤销。

| 来源平台 | 作用 | 曾出现位置（已清理） |
|---|---|---|
| 博查（Bocha）Web Search API | 联网搜索 | `open-earth-engine/open_earth_engine/knowledge/knowledge_mcp_server.py`、`open-earth-engine/oea_service.py` |
| DeepSeek API | 模型推理 | `fix-runtime.bat` |
| DeepSeek API | 模型推理 / 示例配置 | `SYNC_GUIDE.md` |
| apiclaude.cc 图像接口 | 图像生成 | `gpt-image-2-integration-changes.md` |

仓库外本地配置副本（仅记录位置，未修改）：`~/.pilotdeck/pilotdeck.yaml`、
`~/.rsagent/pilotdeck.yaml`、`~/.rsagent/rsagent.yaml`。这些文件由用户本地
持有，建议在平台侧轮换后自行更新。

### 10.5 上游对比方法（可复现）

```powershell
git clone --depth 1 https://github.com/OpenBMB/PilotDeck.git "$env:TEMP\pilotdeck-upstream"
# 对 src、ui/src、apps/desktop/src、scripts、skills、products 逐文件 MD5 比对
# 本地 LICENSE 与上游 LICENSE 的 MD5 均为 11DA06444AFC8233C93D92F2FF286607
```

---

## 十一、最终建议（按投入产出排序）

1. **先做"能开源"的最小闭环**（1～2 天量级）：
   - 保留 `LICENSE`；
   - 新增 `NOTICE`、`THIRD-PARTY-NOTICES.md`、`LICENSES/`；
   - 所有 `package.json` 改 `AGPL-3.0-only`；
   - 修 README 的虚假署名与上游链接；
   - 修 `AuthScreenLayout.tsx` 源码链接；
   - 撤销 4 个 API Key（共 6 处引用）。
2. **再做"能分发"的闭环**：
   - 清理仓库，只保留源码；
   - 安装包/压缩包走 Releases；
   - bundle 内附 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`；
   - 为 `node-bin`/`bun-bin` 补许可证；
   - 若分发 conda 环境，补 GPL/LGPL/MPL 声明与源码链接。
3. **最后做"能长期商用"的闭环**：
   - 明确商标与品牌边界；
   - 建立 CI 许可证扫描；
   - 若做 SaaS，提供源码链接；
   - 若未来引入模型权重，逐个核查许可证。

**如果只能记住一句话：本项目可以商用、可以开源，但必须继续以 AGPL-3.0 开源、保留上游署名、声明修改、向用户提供完整源码；不能闭源，也不能自称是上游官方项目。**
