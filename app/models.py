"""
Define data classes for form data and response configuration.
"""
import json
from dataclasses import dataclass
from typing import Any

# TODO: CHeck again
@dataclass
class FormData:
    form_id: str
    title: str
    created_at: float
    form_url: str

    def to_json(self) -> str:
        return json.dumps({
            "form_id": self.form_id,
            "title": self.title,
            "created_at": self.created_at,
            "form_url": self.form_url
        })

    @classmethod
    def from_json(cls, json_data: str) -> 'FormData':
        data = json.loads(json_data)
        return cls(
            form_id=data["form_id"],
            title=data["title"],
            created_at=data["created_at"],
            form_url=data["form_url"]
        )

@dataclass
class ResponseConfig:
    form_id: str
    some_field: str  # Ví dụ trường, thay bằng các trường thực tế

    def to_json(self) -> str:
        return json.dumps({
            "form_id": self.form_id,
            "some_field": self.some_field
        })

    @classmethod
    def from_json(cls, json_data: str) -> 'ResponseConfig':
        data = json.loads(json_data)
        return cls(
            form_id=data["form_id"],
            some_field=data["some_field"]
        )