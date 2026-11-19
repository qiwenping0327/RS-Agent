"""
任务模板管理
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("rs-engine.template")

# 默认模板目录
DEFAULT_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "templates")


class TemplateManager:
    """
    遥感任务模板管理器

    提供 CRUD 操作，模板以 JSON 文件存储。
    """

    def __init__(self, template_dir: str | None = None):
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        os.makedirs(self.template_dir, exist_ok=True)

    def list_templates(self, category: str | None = None) -> list[dict[str, Any]]:
        """
        列出所有模板

        Args:
            category: 按分类过滤

        Returns:
            模板元数据列表
        """
        templates = []
        for filename in os.listdir(self.template_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.template_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tpl = json.load(f)
                if category and tpl.get("category") != category:
                    continue
                templates.append(tpl)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("读取模板 %s 失败: %s", filename, e)
        return templates

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """
        获取单个模板

        Args:
            template_id: 模板 ID

        Returns:
            模板内容
        """
        filepath = os.path.join(self.template_dir, f"{template_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("读取模板 %s 失败: %s", template_id, e)
            return None

    def create_template(self, template: dict[str, Any]) -> dict[str, Any]:
        """
        创建模板

        Args:
            template: 模板内容，需包含 id 字段

        Returns:
            创建的模板
        """
        template_id = template.get("id")
        if not template_id:
            raise ValueError("模板必须包含 id 字段")

        template["created_at"] = datetime.utcnow().isoformat()
        template["updated_at"] = template["created_at"]

        filepath = os.path.join(self.template_dir, f"{template_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        logger.info("创建模板: %s", template_id)
        return template

    def update_template(self, template_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """
        更新模板

        Args:
            template_id: 模板 ID
            updates: 更新内容

        Returns:
            更新后的模板
        """
        template = self.get_template(template_id)
        if not template:
            return None

        template.update(updates)
        template["updated_at"] = datetime.utcnow().isoformat()

        filepath = os.path.join(self.template_dir, f"{template_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        logger.info("更新模板: %s", template_id)
        return template

    def delete_template(self, template_id: str) -> bool:
        """
        删除模板

        Args:
            template_id: 模板 ID

        Returns:
            是否删除成功
        """
        filepath = os.path.join(self.template_dir, f"{template_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info("删除模板: %s", template_id)
            return True
        return False
