"""Where the running backend can be reached.

On startup the backend writes ``<APP_DATA>/runtime.json`` with its port and
process id so local clients (the MCP server) can find it. The file is
replaced atomically; a reader must still check that the backend answers,
because a hard kill leaves the file behind.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import Config

RUNTIME_FILE_NAME = "runtime.json"


def runtime_file_path(app_data_path: Optional[str] = None) -> Path:
    return Path(app_data_path or Config.APP_DATA_PATH) / RUNTIME_FILE_NAME


def write_runtime_info(port: int, version: str = "", app_data_path: Optional[str] = None) -> Path:
    path = runtime_file_path(app_data_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "port": int(port),
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "version": version,
    }
    temp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(info), encoding="utf-8")
    os.replace(temp_path, path)
    return path


def read_runtime_info(app_data_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return the recorded runtime info, or None if missing or unreadable."""
    path = runtime_file_path(app_data_path)
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(info, dict) or not isinstance(info.get("port"), int):
        return None
    return info
