# Third-Party Notices

This file lists third-party software and assets that are distributed with
RsAgent, either in this source repository or in the desktop application
packages. It is provided in addition to the root `LICENSE` (AGPL-3.0) and
`NOTICE`.

The source repository does not commit `node_modules/` or the large offline
dependency archives under `dependencies/`. Those are installed or distributed
separately. When they are distributed, the notices below apply.

---

## 1. Upstream project

| Component | License | Source |
|---|---|---|
| PilotDeck | AGPL-3.0 | https://github.com/OpenBMB/PilotDeck |

RsAgent is a modified version of PilotDeck. Upstream copyright is held by the
PilotDeck project authors and contributors. See `NOTICE` for the modification
statement and the non-endorsement statement.

---

## 2. Bundled runtimes

| Component | Version | License | License text |
|---|---|---|---|
| Node.js | 22.14.0 (license text from the official Node.js 22 distribution) | MIT (plus third-party components documented in the Node.js LICENSE) | `LICENSES/Node.js-LICENSE.txt`, `apps/desktop/resources/node-bin/LICENSE` |
| Bun | see bundled build | MIT; the binary statically links JavaScriptCore/WebKit, which are LGPL-2 licensed | `LICENSES/Bun-LICENSE.md`, `apps/desktop/resources/bun-bin/LICENSE.md` |
| Electron | 39.8.10 | MIT | `LICENSE.electron.txt` in the installed application |
| Chromium | bundled with Electron | BSD-style and other licenses | `LICENSES.chromium.html` in the installed application |

The Node.js and Bun binaries are **not committed to the source repository**
(see `.gitignore`); they are distributed through GitHub Releases or downloaded
from their official distributions. When they are redistributed, keep the
runtime's license file together with the binary. Bun's license text also
explains the LGPL-2 relinking obligation for its statically linked
JavaScriptCore/WebKit components.

---

## 3. npm dependencies

The application bundles npm dependencies into its package. Most are licensed
under MIT, ISC, Apache-2.0, BSD-2-Clause, or BSD-3-Clause. The following
dependencies need particular attention:

| Package | Version | License | Notes |
|---|---|---|---|
| `mupdf` | 1.27.0 | AGPL-3.0-or-later | Same copyleft family as this project. Keep this package's license file with distributions. Any proprietary/closed-source distribution would require replacing this dependency or obtaining a separate license. |
| `@img/sharp-win32-x64` | 0.34.5 | Apache-2.0 AND LGPL-3.0-or-later | Includes the native libvips/sharp binary. Apache-2.0 text is in `LICENSES/Apache-2.0.txt`; LGPL-3.0 text is in `LICENSES/LGPL-3.0.txt` (it incorporates GPL-3.0, see `LICENSES/GPL-3.0.txt`). |
| `@img/sharp-libvips-linux-x64` | 1.2.4 | LGPL-3.0-or-later | Same as above for Linux builds. |
| `web-push` | 3.6.7 | MPL-2.0 | Keep the package LICENSE file; full text is in `LICENSES/MPL-2.0.txt`. Modifications to MPL-covered files must be made available under MPL-2.0. |
| `@fontsource-variable/inter` | 5.2.8 | OFL-1.1 | SIL Open Font License. Full text is in `LICENSES/OFL-1.1.txt`; do not use a Reserved Font Name for modified font files. |
| `jszip` | 3.10.1 | MIT OR GPL-3.0-or-later | This project uses the MIT option. |
| `caniuse-lite` | 1.0.30001793 | CC-BY-4.0 | Build-time data. Attribution is required if the data is redistributed. |
| `busboy` | 1.6.0 | MIT (LICENSE file; no `license` field in package.json) | Keep the package LICENSE file. |
| `streamsearch` | 1.1.0 | MIT (LICENSE file; no `license` field in package.json) | Keep the package LICENSE file. |
| `spawn-command` | 0.2.2 | ISC (LICENSE file; no `license` field in package.json) | Keep the package LICENSE file. |
| `@vscode/ripgrep` | 1.18.0 | MIT | Includes the ripgrep binary; keep the package LICENSE file. |

The remaining npm dependencies are distributed under their respective
permissive licenses. Most packages in `node_modules/` and in the generated
bundle archives include their own license file; for packages whose license is
recorded only in `package.json`, the license identifier and attribution are
retained in that metadata. To regenerate a complete list for a release, run:

```bash
pnpm licenses list --prod
# or
npx license-checker --production
```

---

## 4. Python and conda environment (distributed separately)

The offline Python environment under `dependencies/` is not part of the source
repository. If it is distributed with an offline installer, the following
components require their license texts and source-availability information.

The environment was scanned from `conda-meta` and contains 153 conda packages.
Most are MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, Zlib, PSF-2.0, or ISC.
The copyleft and special components are:

| Package | Version | License |
|---|---|---|
| `libnsl` | 2.0.0 | GPL-2.0-only |
| `readline` | 8.3 | GPL-3.0-only |
| `ld_impl_linux-64` | 2.44 | GPL-3.0-only |
| `libgcc`, `libgcc-ng`, `libgfortran`, `libgfortran5`, `libstdcxx`, `libstdcxx-ng` | 15.2.0 | GPL-3.0-only WITH GCC-exception-3.1 |
| `geos` | 3.10.6 | LGPL-2.1-only |
| `libiconv` | 1.18 | LGPL-2.1-only |
| `libglib` | 2.86.0 | LGPL-2.1-or-later |
| `cairo` | 1.18.4 | LGPL-2.1-or-later or MPL-1.1 |
| `fribidi` | 1.0.16 | LGPL-2.1-or-later |
| `keyutils` | 1.6.3 | LGPL-2.1-or-later |
| `xz` | 5.8.2 | LGPL-2.1-or-later and GPL-2.0-or-later and 0BSD |
| `graphite2` | 1.3.15 | LGPL-2.0-or-later |
| `freexl` | 2.0.0 | MPL-1.1 |
| `libspatialite` | 5.1.0 | MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later |
| `freetype`, `libfreetype`, `libfreetype6` | 2.14.3 | GPL-2.0-only OR FTL (this build uses the FTL option) |

Additional non-standard licenses in the environment include HPND, IJG, TCL,
`blessing`, `curl`, `zlib-acknowledgement`, `LicenseRef-Qhull`, and
CC-PDDC OR BSD-3-Clause. Their license files are included in the corresponding
`conda-meta/*.json` and package directories.

Source availability: for each conda package, the corresponding source is
available from the conda-forge feedstock or the upstream project named in its
`conda-meta` metadata. If you distribute the environment, include the full
license texts and a written offer or link to those sources. Do not describe
the whole environment as AGPL-3.0; each component keeps its own license.

The Python packages installed from `pip` (for example NumPy, aiohttp,
rasterio, GeoPandas, Shapely, pyproj, Pillow, scikit-image, SciPy, FastAPI,
Uvicorn, Jinja2, Markdown, WeasyPrint, and their transitive dependencies) keep
their own licenses (BSD, Apache-2.0, MIT, HPND, PSF-2.0, etc.). Their wheel
metadata and license files are included in the `pip-deps` archives.

---

## 5. Skills

| Skill | License | Attribution / license file |
|---|---|---|
| `skills/frontend-slides` | MIT | Copyright (c) 2025 Zara Zhang; `skills/frontend-slides/LICENSE` |
| `skills/skill-creator` | Apache-2.0 | `skills/skill-creator/LICENSE.txt` |
| `skills/find-skills` | MIT | Copyright (c) 2026 Vercel, Inc.; `skills/find-skills/LICENSE` |
| `skills/minimax-pdf` | MIT | Copyright (c) 2026 MiniMax; `skills/minimax-pdf/LICENSE` |
| `skills/karpathy-guidelines` | MIT (declared in SKILL.md) | Derived from Andrej Karpathy's observations; no separate upstream LICENSE file was provided |
| `skills/doc-craft`, `skills/rs-cartography`, `skills/pilotdeck-skills-migration` | AGPL-3.0 (part of this project) | Covered by the root `LICENSE` |

---

## 6. Fonts and static assets

| Asset | License / status |
|---|---|
| Inter variable font (`@fontsource-variable/inter`) | SIL Open Font License 1.1; license file is included in the npm package |
| `assets/banner.png`, `assets/*.gif`, `assets/community/*` | Derived from the upstream PilotDeck repository; distributed under AGPL-3.0 as part of this project. Upstream logos and community materials are not used as RsAgent trademarks. |
| `ui/public/logo*`, `ui/public/favicon*` | Project branding assets. Ensure they do not reproduce upstream trademarks. |
| `manual-images/*.svg` | Project documentation assets, AGPL-3.0. |

---

## 7. How to comply when redistributing

1. Keep the root `LICENSE`, `NOTICE`, and this file together with the source
   and with any binary package.
2. Keep the license files inside bundled npm packages and runtime directories.
3. For the desktop application, include `LICENSES/` and the Electron/Chromium
   license files in the installed application.
4. Provide the corresponding source for the exact released version (tag or
   commit). See the "Source code for binary releases" section in `README.md`.
5. If you distribute the offline conda environment, include the GPL/LGPL/MPL
   license texts and the source-availability information described in section 4.
