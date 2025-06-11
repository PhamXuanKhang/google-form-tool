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
    def from_url(cls, url: str, **kwargs):
        """
        Create a Form instance from a given URL, automatically generating a deterministic ID.

        Args:
            url (str): The form's URL to generate the ID from.
            **kwargs: Other keyword arguments for initializing the Form (e.g., title, description).

        Returns:
            Form: A new Form instance with ID generated from the URL.
        """
        return cls(id=f"f_{generate_uuid_from_url(url)}", url=url, **kwargs)


class FormData(BaseModel):
    """
    Represents the in-memory or on-disk database structure that stores multiple forms.

    Attributes:
        forms (List[Form]): List of all forms in the database.
    """
    forms: Optional[List[Form]]
