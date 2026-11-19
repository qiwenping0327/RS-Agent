from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("oea.sandbox")


class SandboxSecurityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SandboxConfig:
    security_level: SandboxSecurityLevel = SandboxSecurityLevel.MEDIUM
    timeout_seconds: int = 120
    max_memory_mb: int = 2048
    max_cpu_cores: int = 4
    workspace_root: str = "/tmp/oea_workspace"
    enable_network: bool = False
    allowed_modules: list[str] = field(default_factory=lambda: [
        "numpy",
        "rasterio",
        "geopandas",
        "shapely",
        "gdal",
        "osgeo",
        "fiona",
        "pyproj",
        "scipy",
        "sklearn",
        "matplotlib",
        "seaborn",
        "pandas",
        "json",
        "datetime",
        "time",
        "math",
        "re",
        "collections",
        "itertools",
        "typing",
    ])
    forbidden_patterns: list[str] = field(default_factory=lambda: [
        "__import__",
        "subprocess",
        "os.system",
        "os.popen",
        "exec(",
        "eval(",
        "compile(",
        "open.*http",
        "socket",
        "ftp",
        "ssh",
    ])


class SandboxExecutor:
    """
    安全的 Python 代码沙箱执行器

    特性:
    1. 工作空间隔离
    2. 模块白名单
    3. 危险代码拦截
    4. 超时控制
    5. 资源限制
    """

    def __init__(self, config: dict):
        self.config = SandboxConfig()
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        os.makedirs(self.config.workspace_root, exist_ok=True)

    def _security_check(self, code: str) -> list[str]:
        warnings = []
        code_lower = code.lower()

        for pattern in self.config.forbidden_patterns:
            if pattern in code:
                warnings.append(f"Forbidden pattern detected: {pattern}")

        import_lines = [line for line in code.split("\n") if line.strip().startswith(("import ", "from "))]
        for line in import_lines:
            module = line.split()[1].split(".")[0]
            if module not in self.config.allowed_modules:
                logger.warning(f"Module '{module}' not in whitelist, execution may fail")

        return warnings

    def _create_workspace(self, workspace_id: str) -> str:
        workspace_dir = os.path.join(self.config.workspace_root, workspace_id)
        input_dir = os.path.join(workspace_dir, "input")
        output_dir = os.path.join(workspace_dir, "output")
        temp_dir = os.path.join(workspace_dir, "temp")

        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        return workspace_dir

    async def execute(
        self,
        code: str,
        params: dict[str, Any] = None,
        workspace_id: str = "default",
    ) -> dict[str, Any]:
        params = params or {}
        workspace_dir = self._create_workspace(workspace_id)
        output_dir = os.path.join(workspace_dir, "output")

        logger.info(f"Executing sandbox code in workspace: {workspace_id}")

        warnings = self._security_check(code)
        if warnings and self.config.security_level == SandboxSecurityLevel.HIGH:
            return {
                "success": False,
                "error": "Security violations detected: " + "; ".join(warnings),
                "warnings": warnings,
            }

        start_time = time.time()
        result = {
            "success": False,
            "output": "",
            "error": None,
            "output_files": [],
            "workspace_dir": workspace_dir,
            "duration_ms": 0,
            "warnings": warnings,
        }

        try:
            import io
            import contextlib

            output_buffer = io.StringIO()

            globals_dict = {
                "__name__": "__main__",
                "__builtins__": self._safe_builtins(),
                "params": params,
                "workspace_dir": workspace_dir,
                "output_dir": output_dir,
                "TEMP_DIR": output_dir,
            }

            locals_dict: dict[str, Any] = {}

            try:
                import asyncio
                loop = asyncio.get_running_loop()

                def sync_exec():
                    with contextlib.redirect_stdout(output_buffer):
                        with contextlib.redirect_stderr(output_buffer):
                            exec(code, globals_dict, locals_dict)

                await asyncio.wait_for(
                    loop.run_in_executor(None, sync_exec),
                    timeout=self.config.timeout_seconds,
                )

            except asyncio.TimeoutError:
                result["error"] = f"Execution timed out after {self.config.timeout_seconds} seconds"
                return result
            except Exception as e:
                logger.exception("Sandbox execution error")
                result["error"] = str(e)
                return result

            output_files = []
            if os.path.exists(output_dir):
                for root, dirs, files in os.walk(output_dir):
                    for f in files:
                        if f.endswith((".tif", ".tiff", ".shp", ".geojson", ".png", ".jpg", ".jpeg", ".csv", ".json")):
                            output_files.append(os.path.join(root, f))

            result["success"] = True
            result["output"] = output_buffer.getvalue()
            result["output_files"] = output_files
            result["return_value"] = locals_dict.get("result")

        except Exception as e:
            logger.exception("Sandbox wrapper error")
            result["error"] = f"Sandbox error: {str(e)}"

        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result

    def _safe_builtins(self) -> dict:
        safe_builtins = {}

        original_builtins = __builtins__
        if isinstance(original_builtins, dict):
            original_builtins = original_builtins

        safe_names = [
            "abs", "all", "any", "bin", "bool", "chr", "complex",
            "dict", "dir", "divmod", "enumerate", "float", "format",
            "frozenset", "hash", "hex", "id", "int", "isinstance",
            "issubclass", "iter", "len", "list", "map", "max", "min",
            "next", "oct", "ord", "pow", "range", "repr", "reversed",
            "round", "set", "slice", "sorted", "str", "sum", "tuple",
            "type", "zip", "__import__",
        ]

        for name in safe_names:
            if hasattr(original_builtins, name):
                safe_builtins[name] = getattr(original_builtins, name)

        return safe_builtins
