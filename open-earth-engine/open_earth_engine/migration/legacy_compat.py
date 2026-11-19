from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional

logger = logging.getLogger("oea.legacy_compat")

RS_ENGINE_PATH = "/root/PilotDeck/rs-engine"
if RS_ENGINE_PATH not in sys.path:
    sys.path.insert(0, RS_ENGINE_PATH)

HAS_LEGACY_TOOLS = False

try:
    from rs_engine.earth_agent_tools.utils import read_image, read_image_uint8, get_geotransform
    from rs_engine.earth_agent_tools.index import calculate_ndvi, calculate_ndwi, calculate_evi, calculate_nbr
    HAS_LEGACY_TOOLS = True
    logger.info("Legacy earth_agent_tools loaded successfully")
except ImportError as e:
    HAS_LEGACY_TOOLS = False
    logger.warning(f"Legacy earth_agent_tools not available: {e}")

    def read_image(file_path):
        try:
            import rasterio
            import numpy as np

            with rasterio.open(file_path) as src:
                img = src.read()
                if img.shape[0] == 1:
                    return img[0]
                return np.transpose(img, (1, 2, 0))
        except Exception as e:
            raise RuntimeError(f"read_image failed: {e}")


def get_temp_dir() -> str:
    env_dir = os.environ.get("OEA_OUTPUT_DIR")
    if env_dir:
        temp_dir = os.path.join(env_dir, "legacy_output")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    default = "/tmp/oea_legacy_output"
    os.makedirs(default, exist_ok=True)
    return default


TEMP_DIR = get_temp_dir()


class LegacyScriptAdapter:
    """存量脚本适配器 - earth_agent_tools 兼容层"""

    API_COMPAT_MAP = {
        "read_image": {"module": "rs_engine.earth_agent_tools.utils"},
        "read_image_uint8": {"module": "rs_engine.earth_agent_tools.utils"},
        "get_geotransform": {"module": "rs_engine.earth_agent_tools.utils"},
        "calculate_ndvi": {"module": "rs_engine.earth_agent_tools.index"},
        "calculate_ndwi": {"module": "rs_engine.earth_agent_tools.index"},
        "calculate_evi": {"module": "rs_engine.earth_agent_tools.index"},
        "calculate_nbr": {"module": "rs_engine.earth_agent_tools.index"},
    }

    def adapt_script(self, legacy_code: str) -> str:
        imports_needed = set()

        for api_name in self.API_COMPAT_MAP:
            if api_name in legacy_code:
                imports_needed.add(api_name)

        compat_header = self._build_compat_header(imports_needed)
        path_adapter = self._build_path_adapter()

        return "\n".join([
            "# ===========================================",
            "# OpenEarthAgent 脚本自动适配",
            "# ===========================================",
            "",
            compat_header,
            "",
            path_adapter,
            "",
            "# ===========================================",
            "# 用户原始代码",
            "# ===========================================",
            "",
            legacy_code,
        ])

    def _build_compat_header(self, imports: set[str]) -> str:
        lines = [
            "import sys",
            "import os",
            "",
            "RS_ENGINE_PATH = '/root/PilotDeck/rs-engine'",
            "if RS_ENGINE_PATH not in sys.path:",
            "    sys.path.insert(0, RS_ENGINE_PATH)",
            "",
        ]

        if "read_image" in imports:
            lines.extend([
                "try:",
                "    from rs_engine.earth_agent_tools.utils import read_image, read_image_uint8, get_geotransform",
                "    HAS_LEGACY_UTILS = True",
                "except ImportError:",
                "    HAS_LEGACY_UTILS = False",
                "    def read_image(file_path):",
                "        import rasterio",
                "        import numpy as np",
                "        with rasterio.open(file_path) as src:",
                "            img = src.read()",
                "            if img.shape[0] == 1: return img[0]",
                "            return np.transpose(img, (1, 2, 0))",
                "",
            ])

        if "calculate_ndvi" in imports or "calculate_ndwi" in imports:
            lines.extend([
                "try:",
                "    from rs_engine.earth_agent_tools.index import calculate_ndvi, calculate_ndwi, calculate_evi",
                "    HAS_LEGACY_INDEX = True",
                "except ImportError:",
                "    HAS_LEGACY_INDEX = False",
                "",
            ])

        return "\n".join(lines)

    def _build_path_adapter(self) -> str:
        return """
def _resolve_path(path):
    if os.path.isabs(path):
        return path
    output_dir = os.environ.get('OEA_OUTPUT_DIR', '/tmp')
    temp_dir = os.environ.get('OEA_TEMP_DIR', '/tmp')
    return os.path.join(temp_dir, os.path.basename(path))

TEMP_DIR = os.environ.get('OEA_OUTPUT_DIR', '/tmp/oea_output')
os.makedirs(TEMP_DIR, exist_ok=True)
"""

    def analyze_script(self, code: str) -> dict:
        warnings = []

        dangerous_patterns = [
            ("subprocess", "系统命令执行（沙箱中会被拦截）"),
            ("os.system", "系统命令执行（沙箱中会被拦截）"),
            ("exec(", "动态代码执行（不推荐）"),
            ("eval(", "动态代码执行（不推荐）"),
            ("requests.get", "网络访问（沙箱中会被拦截）"),
            ("urllib.request", "网络访问（沙箱中会被拦截）"),
        ]

        for pattern, desc in dangerous_patterns:
            if pattern in code:
                warnings.append(f"检测到 {desc}")

        if "gdal." in code and "rasterio" not in code:
            warnings.append("建议使用 rasterio 替代直接 GDAL 调用")

        legacy_apis = [
            api for api in self.API_COMPAT_MAP.keys()
            if api in code
        ]

        return {
            "uses_legacy_tools": len(legacy_apis) > 0,
            "legacy_apis": legacy_apis,
            "warnings": warnings,
            "adaptable": len(warnings) == 0 or all(
                "沙箱" not in w for w in warnings
            ),
        }


def run_legacy_script(script_code: str) -> dict:
    globals_dict = {
        "__name__": "__main__",
        "TEMP_DIR": TEMP_DIR,
        "read_image": read_image,
        "calculate_ndvi": calculate_ndvi if HAS_LEGACY_TOOLS else None,
        "calculate_ndwi": calculate_ndwi if HAS_LEGACY_TOOLS else None,
        "calculate_evi": calculate_evi if HAS_LEGACY_TOOLS else None,
    }

    locals_dict: dict[str, Any] = {}

    try:
        exec(script_code, globals_dict, locals_dict)

        output_files = []
        if os.path.exists(TEMP_DIR):
            for root, dirs, files in os.walk(TEMP_DIR):
                for f in files:
                    if f.endswith((".tif", ".tiff", ".shp", ".geojson", ".png", ".jpg")):
                        output_files.append(os.path.join(root, f))

        return {
            "success": True,
            "output_files": output_files,
        }

    except Exception as e:
        logger.exception(f"Legacy script execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
