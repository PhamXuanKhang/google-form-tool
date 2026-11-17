"""Named answer-configuration templates in the ``templates`` table of db.json."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from tinydb import Query, TinyDB

from app.services.storage_service import _DB_WRITE_LOCK

TEMPLATES_TABLE = "templates"


class TemplateStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, template: Dict[str, Any]) -> Dict[str, Any]:
        record = {"template_id": uuid.uuid4().hex, **template}
        with _DB_WRITE_LOCK, TinyDB(self.db_path) as db:
            db.table(TEMPLATES_TABLE).insert(record)
        return record

    def get(self, template_id: str) -> Optional[Dict[str, Any]]:
        with TinyDB(self.db_path) as db:
            found = db.table(TEMPLATES_TABLE).get(Query().template_id == template_id)
        return dict(found) if found else None

    def list(self) -> List[Dict[str, Any]]:
        with TinyDB(self.db_path) as db:
            records = [dict(record) for record in db.table(TEMPLATES_TABLE).all()]
        records.sort(key=lambda record: record.get("created_at") or "", reverse=True)
        return records

    def delete(self, template_id: str) -> bool:
        with _DB_WRITE_LOCK, TinyDB(self.db_path) as db:
            removed = db.table(TEMPLATES_TABLE).remove(Query().template_id == template_id)
        return bool(removed)
