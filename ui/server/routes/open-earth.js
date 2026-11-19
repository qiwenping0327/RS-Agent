/**
 * OpenEarthAgent API 路由 - 真实执行版
 * 
 * 连接到 Python OpenEarthEngine 服务提供真实的遥感任务执行能力
 */

import { spawn, execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import os from 'os';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = process.env.PILOTDECK_REPO_ROOT || path.resolve(__dirname, '..', '..', '..');
let OEA_SERVICE_PATH = path.join(REPO_ROOT, 'open-earth-engine', 'oea_service.py');

if (!fs.existsSync(OEA_SERVICE_PATH)) {
    const possibleRoots = [
        path.resolve(__dirname, '..', '..', '..'),
        path.resolve(__dirname, '..', '..', '..', '..'),
        path.resolve(os.homedir(), 'AppData', 'Roaming', 'RsAgent', 'runtime', '0.0.11'),
        process.env.PILOT_HOME ? path.join(process.env.PILOT_HOME, '..', 'runtime', '0.0.11') : undefined,
    ].filter(Boolean);
    
    for (const root of possibleRoots) {
        const testPath = path.join(root, 'open-earth-engine', 'oea_service.py');
        if (fs.existsSync(testPath)) {
            OEA_SERVICE_PATH = testPath;
            break;
        }
    }
}

const OEA_SERVICE_PORT = 8765;
let oeaServiceProcess = null;
let oeaServiceReady = false;

/**
 * 动态查找 Python 可执行文件路径
 * 优先级：环境变量 > 硬编码常见路径 > 系统 PATH
 */
function findPythonPath() {
    // 1. 优先使用环境变量
    if (process.env.PILOTDECK_CONDA_PYTHON) {
        const envPath = process.env.PILOTDECK_CONDA_PYTHON;
        if (fs.existsSync(envPath)) {
            console.log('[OPEN-EARTH] 使用环境变量 PILOTDECK_CONDA_PYTHON:', envPath);
            return envPath;
        }
        console.warn('[OPEN-EARTH] PILOTDECK_CONDA_PYTHON 指向的路径不存在:', envPath);
    }

    // 2. 检查常见安装路径（优先 Python 3.10+ 的标准位置）
    const commonPaths = [
        path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'python.exe'),
        path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
        path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
        'C:\\Python313\\python.exe',
        'C:\\Python312\\python.exe',
        'C:\\Python311\\python.exe',
        'C:\\Python310\\python.exe',
        'C:\\Program Files\\Python313\\python.exe',
        'C:\\Program Files\\Python312\\python.exe',
        'C:\\Program Files\\Python311\\python.exe',
        'C:\\Program Files\\Python310\\python.exe',
        'D:\\miniconda3\\python.exe',
        'D:\\anaconda3\\python.exe',
        'C:\\miniconda3\\python.exe',
        'C:\\anaconda3\\python.exe',
        'C:\\ProgramData\\miniconda3\\python.exe',
        'C:\\ProgramData\\Anaconda3\\python.exe',
    ];

    // 收集所有存在的 Python 路径，然后检查版本
    const candidates = commonPaths.filter(p => fs.existsSync(p));

    // 3. 也从系统 PATH 查找
    try {
        const result = execSync('where python', { stdio: ['ignore', 'pipe', 'ignore'], timeout: 5000 }).toString('utf8').trim();
        const lines = result.split('\n').map(l => l.trim()).filter(Boolean);
        for (const line of lines) {
            if (!line.includes('Microsoft') && !line.includes('WindowsApps') && fs.existsSync(line) && !candidates.includes(line)) {
                candidates.push(line);
            }
        }
    } catch (e) {
        console.warn('[OPEN-EARTH] 无法从系统 PATH 查找 Python');
    }

    // 4. 逐个检查版本，返回第一个 Python >= 3.10 的
    for (const p of candidates) {
        if (checkPythonVersion(p)) {
            console.log('[OPEN-EARTH] 找到 Python 3.10+:', p);
            return p;
        }
        console.warn('[OPEN-EARTH] 跳过 Python (版本太旧):', p);
    }

    console.error('[OPEN-EARTH] 未找到 Python 3.10+ 安装！请安装 Python 3.10+ 并添加到系统 PATH');
    return null;
}

function checkPythonVersion(pythonExe) {
    try {
        const result = execSync(`"${pythonExe}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`, {
            stdio: ['ignore', 'pipe', 'ignore'],
            timeout: 5000,
        }).toString('utf8').trim();
        const [major, minor] = result.split('.').map(Number);
        if (major > 3 || (major === 3 && minor >= 10)) {
            return true;
        }
        console.warn(`[OPEN-EARTH] Python 版本 ${result} < 3.10`);
        return false;
    } catch (e) {
        console.warn(`[OPEN-EARTH] 无法检查 Python 版本: ${pythonExe}`);
        return false;
    }
}

function ensurePythonDependencies(pythonExe) {
    // Check and install open-earth-engine dependencies: aiohttp, numpy
    const requiredPkgs = ['aiohttp', 'numpy'];
    const importCmd = `"${pythonExe}" -c "import aiohttp, numpy"`;
    try {
        execSync(importCmd, { stdio: ['ignore', 'ignore', 'ignore'], timeout: 15000 });
        console.log('[OPEN-EARTH] Python 依赖已就绪: aiohttp, numpy');
        return true;
    } catch (e) {
        console.log('[OPEN-EARTH] 正在安装 Python 依赖: aiohttp, numpy ...');
    }

    try {
        const installCmd = `"${pythonExe}" -m pip install aiohttp numpy --quiet`;
        const result = execSync(installCmd, { stdio: ['ignore', 'pipe', 'pipe'], timeout: 180000 });
        console.log('[OPEN-EARTH] Python 依赖安装完成');
        return true;
    } catch (e) {
        const stderr = (e && e.stderr) ? e.stderr.toString().slice(-400) : '';
        console.error('[OPEN-EARTH] Python 依赖安装失败:', stderr || e.message);
        return false;
    }
}

function startOpenEarthEngineService() {
    return new Promise(async (resolve, reject) => {
        if (oeaServiceProcess) {
            resolve(true);
            return;
        }

        console.log('[OPEN-EARTH] 正在启动 Python OpenEarthEngine 服务...');
        console.log('[OPEN-EARTH] REPO_ROOT:', REPO_ROOT);
        console.log('[OPEN-EARTH] OEA_SERVICE_PATH:', OEA_SERVICE_PATH);
        
        // 动态查找 Python 路径
        const pythonPath = findPythonPath();
        if (!pythonPath) {
            const error = new Error('Python not found. Please install Python 3.10+');
            console.error('[OPEN-EARTH] Python 未安装，无法启动服务');
            reject(error);
            return;
        }
        console.log('[OPEN-EARTH] 使用 Python 路径:', pythonPath);

        // 启动前确保 aiohttp/numpy 已安装
        if (!ensurePythonDependencies(pythonPath)) {
            console.warn('[OPEN-EARTH] 依赖安装未成功，继续尝试启动服务...');
        }
        
        const childProcess = spawn(pythonPath, [OEA_SERVICE_PATH], {
            cwd: REPO_ROOT,
            env: {
                ...process.env,
                RS_WORKSPACE: path.join(REPO_ROOT, 'data'),
                RS_ENGINE_HOME: path.join(REPO_ROOT, 'rs-engine')
            },
            stdio: ['ignore', 'pipe', 'pipe']
        });

        function checkReady(msg) {
            if (!oeaServiceReady && (msg.includes('OpenEarthEngine 服务已启动') || msg.includes('http://127.0.0.1:8765'))) {
                oeaServiceReady = true;
                console.log('[OPEN-EARTH] Python 服务已就绪');
                resolve(true);
            }
        }

        childProcess.stdout.on('data', (data) => {
            const msg = data.toString();
            console.log('[OEA-PYTHON]', msg.trim());
            checkReady(msg);
        });

        childProcess.stderr.on('data', (data) => {
            const msg = data.toString();
            console.log('[OEA-PYTHON]', msg.trim());
            checkReady(msg);
        });

        childProcess.on('close', (code) => {
            console.log('[OPEN-EARTH] Python 服务退出，代码:', code);
            oeaServiceProcess = null;
            oeaServiceReady = false;
        });

        childProcess.on('error', (err) => {
            console.error('[OPEN-EARTH] Python 服务启动失败:', err);
            oeaServiceProcess = null;
            reject(err);
        });

        oeaServiceProcess = childProcess;

        setTimeout(() => {
            if (!oeaServiceReady) {
                console.log('[OPEN-EARTH] 等待 Python 服务初始化中...');
            }
        }, 2000);
    });
}

async function checkPythonServiceRunning() {
    try {
        const { default: fetch } = await import('node-fetch');
        const response = await fetch(`http://127.0.0.1:${OEA_SERVICE_PORT}/api/open-earth/knowledge/stats`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            signal: AbortSignal.timeout(3000),
        });
        if (response.ok) {
            oeaServiceReady = true;
            return true;
        }
    } catch (e) {
        // Service not reachable
    }
    return false;
}

async function proxyToPythonService(endpoint, body) {
    if (!oeaServiceReady) {
        // First check if the Python service is already running (e.g., started manually)
        const alreadyRunning = await checkPythonServiceRunning();
        if (!alreadyRunning) {
            try {
                await startOpenEarthEngineService();
            } catch (e) {
                console.error('[OPEN-EARTH] 无法启动 Python 服务:', e);
                return {
                    success: false,
                    error: 'Python 服务启动失败',
                    error_code: 'SERVICE_START_FAILED'
                };
            }
        }
    }

    return new Promise((resolve, reject) => {
        import('node-fetch').then(async ({ default: fetch }) => {
            try {
                const url = `http://127.0.0.1:${OEA_SERVICE_PORT}${endpoint}`;
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body || {})
                });

                const result = await response.json();
                resolve(result);
            } catch (e) {
                console.error('[OPEN-EARTH] 代理请求失败:', e);
                reject(e);
            }
        }).catch(reject);
    });
}

async function proxyGetToPythonService(endpoint) {
    if (!oeaServiceReady) {
        const alreadyRunning = await checkPythonServiceRunning();
        if (!alreadyRunning) {
            try {
                await startOpenEarthEngineService();
            } catch (e) {
                console.error('[OPEN-EARTH] 无法启动 Python 服务:', e);
                return {
                    success: false,
                    error: 'Python 服务启动失败',
                    error_code: 'SERVICE_START_FAILED'
                };
            }
        }
    }

    return new Promise((resolve, reject) => {
        import('node-fetch').then(async ({ default: fetch }) => {
            try {
                const url = `http://127.0.0.1:${OEA_SERVICE_PORT}${endpoint}`;
                const response = await fetch(url, { method: 'GET' });
                const result = await response.json();
                resolve(result);
            } catch (e) {
                console.error('[OPEN-EARTH] 代理 GET 请求失败:', e);
                reject(e);
            }
        }).catch(reject);
    });
}

async function proxyToPythonServiceWithMethod(endpoint, method, body) {
    if (!oeaServiceReady) {
        try {
            await startOpenEarthEngineService();
        } catch (e) {
            console.error('[OPEN-EARTH] 无法启动 Python 服务:', e);
            return {
                success: false,
                error: 'Python 服务启动失败',
                error_code: 'SERVICE_START_FAILED'
            };
        }
    }

    return new Promise((resolve, reject) => {
        import('node-fetch').then(async ({ default: fetch }) => {
            try {
                const url = `http://127.0.0.1:${OEA_SERVICE_PORT}${endpoint}`;
                const options = { method };
                if (body && (method === 'POST' || method === 'PUT')) {
                    options.headers = { 'Content-Type': 'application/json' };
                    options.body = JSON.stringify(body);
                }
                const response = await fetch(url, options);
                const result = await response.json();
                resolve({ data: result, status: response.status });
            } catch (e) {
                console.error('[OPEN-EARTH] 代理请求失败:', e);
                reject(e);
            }
        }).catch(reject);
    });
}

function createOpenEarthRouter() {
    const router = {
        async route(req, res) {
            const body = req.body || {};
            if (!body.task_description) {
                return res.status(400).json({
                    error: { code: 'missing_task_description', message: '缺少 task_description' }
                });
            }

            try {
                const result = await proxyToPythonService('/api/open-earth/route', body);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] route 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async decompose(req, res) {
            const body = req.body || {};
            if (!body.task_description) {
                return res.status(400).json({
                    error: { code: 'missing_task_description' }
                });
            }

            try {
                const result = await proxyToPythonService('/api/open-earth/decompose', body);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] decompose 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async orchestrate(req, res) {
            const body = req.body || {};
            if (!body.task_description) {
                return res.status(400).json({
                    error: { code: 'missing_task_description' }
                });
            }

            console.log('[OPEN-EARTH] 真实编排执行:', body.task_description.substring(0, 60));

            try {
                const result = await proxyToPythonService('/api/open-earth/orchestrate', body);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] orchestrate 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async status(req, res) {
            const { taskId } = req.params;

            try {
                const result = await proxyGetToPythonService(`/api/open-earth/status/${taskId}`);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] status 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeSearch(req, res) {
            const body = req.body || {};
            if (!body.query) {
                return res.status(400).json({
                    error: { code: 'missing_query' }
                });
            }

            try {
                const result = await proxyToPythonService('/api/open-earth/knowledge/search', body);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge search 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeList(req, res) {
            try {
                const query = req.url.split('?')[1] || '';
                const result = await proxyGetToPythonService(`/api/open-earth/knowledge${query ? `?${query}` : ''}`);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge list 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeStats(req, res) {
            try {
                const result = await proxyGetToPythonService('/api/open-earth/knowledge/stats');
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge stats 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeGet(req, res) {
            const { entryId } = req.params;
            try {
                const result = await proxyGetToPythonService(`/api/open-earth/knowledge/${entryId}`);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge get 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeCreate(req, res) {
            const body = req.body || {};
            try {
                const result = await proxyToPythonServiceWithMethod('/api/open-earth/knowledge', 'POST', body);
                res.status(result.status || 201).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge create 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeUpdate(req, res) {
            const { entryId } = req.params;
            const body = req.body || {};
            try {
                const result = await proxyToPythonServiceWithMethod(`/api/open-earth/knowledge/${entryId}`, 'PUT', body);
                res.status(result.status || 200).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge update 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeDelete(req, res) {
            const { entryId } = req.params;
            try {
                const result = await proxyToPythonServiceWithMethod(`/api/open-earth/knowledge/${entryId}`, 'DELETE');
                res.status(result.status || 200).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge delete 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeExport(req, res) {
            const body = req.body || {};
            try {
                const result = await proxyToPythonServiceWithMethod('/api/open-earth/knowledge/export', 'POST', body);
                res.status(result.status || 200).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge export 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeImport(req, res) {
            const body = req.body || {};
            try {
                const result = await proxyToPythonServiceWithMethod('/api/open-earth/knowledge/import', 'POST', body);
                res.status(result.status || 200).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge import 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeRebuildIndex(req, res) {
            try {
                const result = await proxyToPythonServiceWithMethod('/api/open-earth/knowledge/rebuild-index', 'POST');
                res.status(result.status || 200).json(result.data);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge rebuild index 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        },

        async knowledgeEnhance(req, res) {
            const body = req.body || {};
            if (!body.query) {
                return res.status(400).json({
                    error: { code: 'missing_query' }
                });
            }

            try {
                const result = await proxyToPythonService('/api/open-earth/knowledge/enhance', body);
                res.json(result);
            } catch (e) {
                console.error('[OPEN-EARTH] knowledge enhance 失败:', e);
                res.status(500).json({
                    error: { code: 'internal_error', message: e.message }
                });
            }
        }
    };

    return router;
}

export {
    startOpenEarthEngineService,
    createOpenEarthRouter,
    OEA_SERVICE_PORT
};
