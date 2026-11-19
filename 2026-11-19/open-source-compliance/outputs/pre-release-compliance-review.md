# RsAgent 发布前 AGPL-3.0 合规复核

- 复核日期：2026-11-19
- 复核对象：`d:\project\PilotDeck`（拟发布仓库：<https://github.com/qiwenping0327/RS-Agent>）
- 上游项目：PilotDeck，<https://github.com/OpenBMB/PilotDeck>，AGPL-3.0
- 复核方式：逐文件检查 + 全仓关键词检索 + 打包产物 tar 内容扫描 + 对照 GNU 官方许可证全文 + 拉取上游 `LICENSE`/`package.json` 核对
- 约束：本次未执行 `git commit`、未推送、未改业务逻辑

---

## 结论摘要

仓库的**声明体系已经成形**：LICENSE、NOTICE、THIRD-PARTY-NOTICES.md、LICENSES/、运行时许可证、安装包 `extraResources`、README 源码入口均已就位；占位符和旧 `OpenBMB/RsAgent` 链接已清零。

但在**真正对外发布前**仍有 3 个必须完成的动作：

1. **把源码推送到 GitHub 仓库**。当前工作目录没有 `.git`，README/NOTICE 中的源码地址在推送前不可访问，AGPL 的“对应源码可获得”尚未实际成立。
2. **重新构建桌面端 bundle 和安装包**。本地 `apps/desktop/resources/*.tar` 是旧构建，扫描确认其中仍含 `OpenBMB PilotDeck AI assistant` 和旧品牌文案；用这些 bundle 打出的安装包会继续显示上游身份。
3. **确认版权人与商标边界**。`NOTICE` 目前写的是 `RsAgent Contributors`，上游素材/Logo 的使用范围需要用户或法务确认。

---

## 一、已满足

### 1. 完整对应源码可获得，且指向本仓库

| 依据 | 位置 | 说明 |
|---|---|---|
| README 英文源码声明 | [README.md](../../../README.md#L467-L474) | 明确二进制发行版的对应源码是本仓库同一 tag/commit |
| README 中文源码声明 | [README.zh.md](../../../README.zh.md#L460-L466) | 同上 |
| NOTICE 源码地址 | [NOTICE](../../../NOTICE#L24-L28) | `https://github.com/qiwenping0327/RS-Agent`，并要求按发行版对应 tag/commit |
| 桌面端应用内入口 | [main.ts](../../../apps/desktop/src/main.ts#L254-L255)、[main.ts](../../../apps/desktop/src/main.ts#L420-L422) | `REPO_URL` 指向本仓库，菜单“项目主页…”通过 `shell.openExternal(REPO_URL)` 打开 |
| 登录页源码入口 | [AuthScreenLayout.tsx](../../../ui/src/components/auth/view/AuthScreenLayout.tsx#L47-L54) | 链接到本仓库，文案 “RsAgent is open source (AGPL-3.0)” |
| 一键安装脚本 | [install.sh](../../../install.sh#L4-L9) | raw URL 与 `REPO_URL` 均指向本仓库 |
| Docker 部署 | [README_DOCKER.md](../../../README_DOCKER.md#L112-L119) | 明确 AGPL §13 并要求保留源码链接 |

结论：只要源码实际推送到该仓库，并通过 tag/commit 与二进制对应，AGPL-3.0 的 Corresponding Source 义务即可成立。

### 2. LICENSE 与上游许可一致

| 依据 | 位置 | 说明 |
|---|---|---|
| 根许可证 | [LICENSE](../../../LICENSE) | GNU AGPL-3.0 完整全文（661 行 / 35,184 字节），含完整条款与结尾 |
| 上游许可证 | <https://raw.githubusercontent.com/OpenBMB/PilotDeck/main/LICENSE> | 上游 `LICENSE` 为 AGPL-3.0 全文；上游 `package.json` 未声明 `license` 字段，许可证以 LICENSE 文件为准 |
| 包元数据 | [package.json](../../../package.json#L5-L6)、[ui/package.json](../../../ui/package.json#L5-L6)、[apps/desktop/package.json](../../../apps/desktop/package.json#L7-L8) | 均声明 `AGPL-3.0-only`，与上游 AGPL-3.0 兼容 |

### 3. NOTICE 的上游署名、修改声明与日期

依据：[NOTICE](../../../NOTICE)

- 第 1-10 行：本作品版权、上游项目名称与上游版权归属；
- 第 12-16 行：非背书/非关联声明，并说明 `PilotDeck` 等名称仅用于描述来源；
- 第 18-22 行：修改声明（遥感工具、桌面打包、品牌与 UI 改动），日期 `2026-11-19` 与实际复核日期一致；
- 第 24-31 行：源码地址与第三方声明指向。

### 4. 通过安装包/二进制分发的用户能拿到源码

| 依据 | 位置 | 说明 |
|---|---|---|
| 安装包附加声明 | [electron-builder.yml](../../../apps/desktop/electron-builder.yml#L72-L80) | `extraResources` 会复制 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`、`LICENSES/` 到安装包 |
| 运行时许可证 | [node-bin/LICENSE](../../../apps/desktop/resources/node-bin/LICENSE)、[bun-bin/LICENSE.md](../../../apps/desktop/resources/bun-bin/LICENSE.md) | 与二进制同目录分发 |
| 应用内入口 | 同第 1 节 | 安装后用户可从菜单/登录页直接打开源码仓库 |
| README 二进制章节 | [README.md](../../../README.md#L467-L474) | 说明每个二进制发行版对应本仓库的 tag/commit |

### 5. AGPL §13（网络服务）是否适用

- **桌面端本地运行不触发 §13**：Electron 应用只在本机 `127.0.0.1` 上启动 UI Server 与 Gateway，没有“远程用户通过网络与修改版交互”的情形。
- **Docker / 自建服务器对外提供服务时触发 §13**：需要在服务界面或文档中向远程用户提供对应源码。
- 仓库已对此作出安排：[README_DOCKER.md](../../../README_DOCKER.md#L112-L119) 明确写出 §13 义务与源码地址；[README.md](../../../README.md#L467-L474) 也给出统一源码入口。
- 如果以后运营 SaaS，同样只需持续提供同一仓库对应 tag/commit 的源码；当前 README 的写法可以覆盖。

### 6. 第三方组件许可声明覆盖

| 类别 | 依据 | 说明 |
|---|---|---|
| npm 依赖 | [THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L44-L74) | 列出 `mupdf`、`sharp/libvips`、`web-push`、Inter 字体、`jszip`、`caniuse-lite`、`busboy`、`streamsearch`、`spawn-command`、`@vscode/ripgrep` 等需特别处理的依赖 |
| Node.js / Bun / Electron / Chromium | [THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L26-L41) | 已说明 Node MIT、Bun MIT + JavaScriptCore/WebKit LGPL-2、Electron/Chromium 自带许可证文件 |
| 许可证全文 | `LICENSES/` | 现有 `Apache-2.0.txt`、`GPL-3.0.txt`、`LGPL-3.0.txt`、`MPL-2.0.txt`、`OFL-1.1.txt`、`Node.js-LICENSE.txt`、`Bun-LICENSE.md` |
| conda 环境 | [THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L78-L121)、[.gitignore](../../../.gitignore#L205-L206) | 153 个 conda 包已分类；`dependencies/` 不入库，当前不随源码仓库分发 |
| 技能 | [THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L125-L134) | `frontend-slides`、`skill-creator`、`find-skills`、`minimax-pdf` 的许可证文件已随仓库保留 |

> 本次复核发现并修复了一个实质问题：`LICENSES/GPL-3.0.txt` 原先只有 314 行（应为 674 行），`LGPL-3.0.txt` 原先只有 75 行（应为 165 行），均为截断文本。现已替换为 GNU 官方全文，第三方 GPL/LGPL 声明才真正成立。

### 7. README 不再暗示上游背书或冒用上游身份

| 依据 | 位置 | 说明 |
|---|---|---|
| 独立分支声明 | [README.md](../../../README.md#L21-L26) | “independent fork”“not endorsed by the upstream project or those organizations” |
| 关于章节 | [README.md](../../../README.md#L32) | 说明基于 PilotDeck、增加遥感能力、由 RsAgent Contributors 维护且未获上游背书 |
| 上游项目章节 | [README.md](../../../README.md#L429-L438) | 再次声明独立维护、非背书 |
| 社区入口 | [README.md](../../../README.md#L394-L402) | 明确上游网站/社群由上游运营，本分支不冒用 |
| 引用章节 | [README.md](../../../README.md#L450-L463) | 明确 BibTeX 引用的是上游项目而非本分支 |
| NOTICE | [NOTICE](../../../NOTICE#L12-L16) | 明确非背书与非关联 |

### 8. 占位符与旧链接已清零

- 全仓检索 `YOUR_GITHUB_USERNAME`、`OpenBMB/RsAgent`：**0 处**。
- 全仓检索 `github.com/pilotdeck`：**0 处**（含 `dist/` 同步修正）。
- 9 个文件、18 处占位符已全部替换为本仓库地址。

### 9. 品牌替换（本次补齐）

- UI 国际化：`ui/src/i18n/locales/en|zh-CN` 的 `sidebar.json`、`settings.json`、`chat.json`、`common.json`、`auth.json` 中用户可见的 `PilotDeck`/`OpenBMB` 已改为 `RsAgent`（保留 JSON key、`pilotdeck` CLI 名、`~/.pilotdeck` 路径等技术标识）。
- 设置页子系统标签与技能提示：`PilotDeckConfigTab.tsx`、`useChatComposerState.ts`。
- TUI：`PilotDeckLogo.tsx` 不再渲染 “PILOTDECK” ASCII 大字，改为 `RsAgent` 字标；`HelpDialog.tsx`、`PromptInput.tsx` 文案已改。
- CLI：`src/cli/pilotdeck.ts` 的显示 model 名与技能迁移标题已改。
- 后端用户可见字符串：`pathSafety.ts`、`agent.ts`、`urlFetcher.ts`（User-Agent）、`validateMarketplaceName.ts`、`AttachmentResolver.ts`、`edgeclaw-memory-core/ui-source/app.js`。
- 启动脚本/文档：`start.sh`、`start-dev.sh`、`deploy/start.sh`、`docker-entrypoint.sh`、`start-dev.bat`、`start-prod.bat`、`README*.md`、`rs-engine/README.md`、`rs-engine/docker-compose.rs.yml`。

---

## 二、仍不满足 / 有缺口

### 2.1 【阻塞】源码尚未推送到 GitHub

- 依据：在工作目录执行 `Test-Path .git` 结果为 `False`。
- 影响：README、NOTICE、安装包内声明的 `https://github.com/qiwenping0327/RS-Agent` 目前在远端还不存在对应源码；AGPL 的“对应源码可获得”只是**纸面声明**，尚未实际成立。
- 处理：由用户初始化/推送源码，并打上与二进制一致的 tag。此动作按约束未由本次执行。

### 2.2 【阻塞】本地 bundle 与安装包是旧构建

- 依据：`apps/desktop/resources/*.tar` 被 [.gitignore](../../../.gitignore#L170-L171) 忽略，不会进源码仓库，但会被 `electron-builder` 打进安装包。
- 扫描结果：
  - `rsagentui-bundle.tar` → `dist/assets/index-DNu8cVhv.js` 仍含 `"OpenBMB PilotDeck AI assistant"` 及旧 i18n 文案；
  - `rsagent-main-bundle.tar` → 仍有 240 处 `PilotDeck`（多数为标识符/注释，但包含旧 UA 与旧错误文案）；
  - `rsagentui-bundle.tar.gz`、`rsagent-main-bundle.0817.tar` 同样为旧产物。
- 影响：如果现在直接用这些 bundle 打安装包，用户看到的仍是上游品牌，且不含本次修正后的文本。
- 处理：按 [WINDOWS_BUILD.md](../../../apps/desktop/WINDOWS_BUILD.md#L135-L173) 重新执行 `npx vite build`、`npx tsc`、重新打三个 bundle，再执行 `electron-builder`。这是发布前构建步骤，不属于源码合规阻塞。

### 2.3 `karpathy-guidelines` 声明 MIT 但缺少许可证全文

- 依据：[skills/karpathy-guidelines/SKILL.md](../../../skills/karpathy-guidelines/SKILL.md#L4) 写有 `license: MIT`，但目录下没有 `LICENSE` 文件；[THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L133) 也注明“no separate upstream LICENSE file was provided”。
- 影响：MIT 声明缺少对应许可证文本，严格来说第三方声明不完整。
- 状态：未擅自补写版权人。

### 2.4 三个技能没有独立许可证文件

- 依据：`skills/doc-craft`、`skills/rs-cartography`、`skills/pilotdeck-skills-migration` 均无 `LICENSE`；[THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L134) 将其归为“AGPL-3.0，属于本项目”。
- 影响：如果这些技能确为项目自研或来自上游 AGPL 代码，则归属正确；如果包含第三方作者内容，需要补充对应许可证与署名。
- 状态：需作者确认来源（见第三节）。

### 2.5 上游素材与商标边界尚未确认

- 依据：[THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L138-L145) 说明 `assets/banner.png`、`assets/*.gif`、`assets/community/*` 来自上游仓库，`ui/public/logo*` 为项目品牌资产。
- 影响：AGPL 授予的是版权许可，不授予商标许可。保留上游 Logo/社群素材用于“来源说明”通常可行，但用于本产品品牌识别可能构成商标性使用。
- 状态：需用户/法务确认。

### 2.6 `NOTICE` 版权人名称待确认

- 依据：[NOTICE](../../../NOTICE#L2) 写的是 `Copyright (c) 2026 RsAgent Contributors`。
- 影响：如果用户希望以个人实名或公司名义主张版权，应替换为正式名称；如果保持匿名/集体署名，也可成立，但需用户确认。

### 2.7 离线 conda 环境未随包分发，相关义务暂未触发

- 依据：[.gitignore](../../../.gitignore#L205-L206) 排除 `dependencies/`；[THIRD-PARTY-NOTICES.md](../../../THIRD-PARTY-NOTICES.md#L78-L121) 已列出 153 个 conda 包中的 GPL/LGPL/MPL 组件及源码获取方式。
- 说明：当前不分发即不触发这些组件的源码提供义务；一旦随离线安装包分发，需要补齐许可证全文与源码获取说明。

### 2.8 构建产物中的旧字符串（非仓库文件）

- 依据：`dist/` 被 [.gitignore](../../../.gitignore#L85) 忽略，`apps/desktop/resources/*.tar` 被第 171 行忽略。
- 说明：这些文件不会进入 GitHub 源码仓库，但会进入本地安装包。发布前重新构建即可消除；本次已同步修正 `dist/main.js`、`dist/.../pathSafety.js`、`dist/.../urlFetcher.js` 中的关键旧链接/文案，但完整重建仍是必要步骤。

---

## 三、需要用户或法务确认

1. **商标使用**：README/NOTICE 中以描述性方式使用 `PilotDeck`、`OpenBMB`、THUNLP、ModelBest、AI9Stars 名称，是否满足描述性合理使用；是否可以在应用内继续显示上游 Logo/演示素材。
2. **版权人名称**：`NOTICE` 与 `package.json` 的 `author` 是否使用实名、公司名或继续使用 `RsAgent Contributors`。
3. **技能来源**：`karpathy-guidelines`、`doc-craft`、`rs-cartography`、`pilotdeck-skills-migration` 的作者与许可证归属；如为第三方内容，需要补 `LICENSE` 与署名。
4. **SaaS/托管服务**：如果未来由你或第三方托管 RsAgent 对外提供网络服务，需确认服务界面持续展示源码入口（§13）；当前 README_DOCKER 已给出模板。
5. **运行时再分发**：如果通过 GitHub Releases 再分发 `node.exe`/`bun.exe`，需保持 `LICENSES/Node.js-LICENSE.txt`、`LICENSES/Bun-LICENSE.md` 与二进制同包；Bun 静态链接的 JavaScriptCore/WebKit 还涉及 LGPL-2 的重链接说明。
6. **离线 conda 包再分发**：如果发布 `dependencies/` 或离线安装包，需就 GPL/LGPL/MPL 组件提供完整许可证文本与源码获取方式（THIRD-PARTY-NOTICES 第 4 节已列清单）。
7. **CLI 名称**：二进制命令仍是 `pilotdeck`，配置路径仍是 `~/.pilotdeck`。README 已说明这是为兼容上游保留的技术标识；是否继续保留由用户决定，不影响 AGPL 合规。

---

## 四、本次实际修改清单

### 占位符
- `README.md`、`README.zh.md`、`NOTICE`、`install.sh`、`README_DOCKER.md`、`ui/src/components/auth/view/AuthScreenLayout.tsx`、`apps/desktop/src/main.ts`、`apps/desktop/WINDOWS_BUILD.md`、`apps/desktop/electron-builder.yml`：18 处占位符 → `https://github.com/qiwenping0327/RS-Agent`。

### 许可证
- `LICENSES/GPL-3.0.txt`：314 行截断版 → GNU 官方 674 行全文。
- `LICENSES/LGPL-3.0.txt`：75 行截断版 → GNU 官方 165 行全文。

### 品牌与身份
- UI i18n（en/zh-CN 共 5 个命名空间）、TUI 字标与提示、CLI 显示名、后端用户可见字符串、启动脚本、README 产品表述、rs-engine 文档与注释。

### 文档修正
- `apps/desktop/WINDOWS_BUILD.md`：修正 `file:///root/RsAgent/...` 坏链接、Onboarding 配置路径、`publish: github` 状态说明。

### 未执行
- 未 `git commit`、未推送、未改业务逻辑、未重新构建安装包。

---

## 五、发布前检查清单

- [ ] 初始化 Git 仓库并推送源码到 `https://github.com/qiwenping0327/RS-Agent`
- [ ] 为二进制发行版打 tag，并在 Release 说明中写明对应源码
- [ ] 重新构建 `rsagentui-bundle.tar`、`rsagent-main-bundle.tar`、`rsagent-memory-core-bundle.tar`
- [ ] 重新执行 `electron-builder` 生成安装包
- [ ] 解包安装包确认包含 `LICENSE`、`NOTICE`、`THIRD-PARTY-NOTICES.md`、`LICENSES/`
- [ ] 确认 `NOTICE` 版权人名称与商标声明
- [ ] 补齐 `karpathy-guidelines` 的 MIT 许可证文本（或确认其归属）
- [ ] 确认 `doc-craft`、`rs-cartography`、`pilotdeck-skills-migration` 的作者与许可证
- [ ] 如果发布 Docker 镜像，在镜像说明或服务界面保留源码链接
