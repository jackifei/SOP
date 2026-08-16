from __future__ import annotations

import sys
import shutil
from pathlib import Path
from typing import Any

import yaml


class ConfigService:
    """统一配置读写服务。

    页面配置保存到 config/<页面名>.yaml；
    流程模板保存到 flow/<模板名>/template.yaml。

    插入点：后续如需远程配置中心，可在此替换读写后端。
    """

    def __init__(self, root_dir: Path | None = None) -> None:
        if root_dir is not None:
            self.root_dir = root_dir
        elif getattr(sys, "frozen", False):
            # PyInstaller 打包后，配置和流程目录放在 exe 同级目录，保证可读可写。
            self.root_dir = Path(sys.executable).resolve().parent
        else:
            self.root_dir = Path(__file__).resolve().parents[2]
        self.config_dir = self.root_dir / "config"
        self.flow_dir = self.root_dir / "flow"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.flow_dir.mkdir(parents=True, exist_ok=True)
        self._copy_bundled_runtime_data()

    def _copy_bundled_runtime_data(self) -> None:
        """PyInstaller 打包后，把 exe 内自带的 config/flow 初始文件复制到 exe 同级目录。"""
        bundle_root = getattr(sys, "_MEIPASS", None)
        if not bundle_root:
            return
        bundle_root = Path(bundle_root)
        for folder_name in ("config", "flow"):
            source = bundle_root / folder_name
            target = self.root_dir / folder_name
            if not source.exists():
                continue
            target.mkdir(parents=True, exist_ok=True)
            for child in source.rglob("*"):
                relative = child.relative_to(source)
                destination = target / relative
                if child.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif not destination.exists():
                    shutil.copy2(child, destination)

    def page_config_path(self, page_name: str) -> Path:
        return self.config_dir / f"{page_name}.yaml"

    def template_dir(self, template_name: str) -> Path:
        directory = self.flow_dir / template_name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def save_page_config(self, page_name: str, data: dict[str, Any]) -> Path:
        path = self.page_config_path(page_name)
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    def load_page_config(self, page_name: str) -> dict[str, Any]:
        path = self.page_config_path(page_name)
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}

    def save_template(self, template_name: str, data: dict[str, Any]) -> Path:
        directory = self.template_dir(template_name)
        path = directory / "template.yaml"
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    def load_template(self, template_name: str) -> dict[str, Any]:
        path = self.template_dir(template_name) / "template.yaml"
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
