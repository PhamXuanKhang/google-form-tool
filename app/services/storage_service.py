from typing import Dict, Any, List, Optional
from tinydb import TinyDB, Query, where
from tinydb.table import Document
from app.models.form_data import FormData, ResponseConfig
from app.models.submission_model import SubmissionBatch

# TODO: Check again
class StorageService:
    """
    Service for storing and retrieving data using TinyDB.
    """

    def __init__(self, db_path: str):
        """
        Initialize the storage service with the given database path.

        Args:
            db_path (str): The path to the json file.
        """
        self.db = TinyDB(db_path)
        self.forms = self.db.table("forms")
        self.configs = self.db.table("configs")
        self.submissions = self.db.table("submissions")

        self.query = Query()

    def save_form_data(self, form_data: FormData) -> str:
        """
        Save the form data to the database.
        
        Args:
            form_data (FormData): The form data to save.

        Returns:
            str: The form id of the saved form.
            """
        self.forms.upsert(Document({
            "form_id": form_data.form_id,
            "title": form_data.title,
            "created_at": form_data.created_at,
            "url": form_data.form_url
        }, doc_id=form_data.form_id))

    def load_form_data(self, form_id: str) -> Optional[FormData]:
        result = self.forms.get(doc_id=form_id)
        if result:
            return FormData.from_json(result["data"])
        return None

    def list_forms(self) -> List[Dict[str, Any]]:
        return sorted([
            {
                "form_id": doc["form_id"],
                "title": doc["title"],
                "created_at": doc["created_at"],
                "url": doc["url"]
            } for doc in self.forms.all()
        ], key=lambda x: x["created_at"], reverse=True)

    def delete_form(self, form_id: str) -> bool:
        self.forms.remove(doc_ids=[form_id])
        self.configs.remove(where("form_id") == form_id)
        self.submissions.remove(where("form_id") == form_id)
        self.screenshots.remove(where("form_id") == form_id)
        return True

    def save_response_config(self, config: ResponseConfig) -> None:
        self.configs.upsert({
            "form_id": config.form_id,
            "data": config.to_json()
        }, where("form_id") == config.form_id)

    def load_response_config(self, form_id: str) -> Optional[ResponseConfig]:
        result = self.configs.get(where("form_id") == form_id)
        if result:
            return ResponseConfig.from_json(result["data"])
        return None

    def save_submission_batch(self, batch: SubmissionBatch) -> None:
        self.submissions.upsert({
            "form_id": batch.form_id,
            "batch_id": batch.batch_id,
            "data": batch.to_json(),
            "created_at": batch.created_at
        }, (where("form_id") == batch.form_id) & (where("batch_id") == batch.batch_id))

    def load_submission_batch(self, form_id: str, batch_id: str) -> Optional[SubmissionBatch]:
        result = self.submissions.get((where("form_id") == form_id) & (where("batch_id") == batch_id))
        if result:
            return SubmissionBatch.from_json(result["data"])
        return None

    def list_submission_batches(self, form_id: str) -> List[Dict[str, Any]]:
        results = self.submissions.search(where("form_id") == form_id)
        return sorted([
            {
                "batch_id": r["batch_id"],
                "created_at": r["created_at"],
                "total_tasks": SubmissionBatch.from_json(r["data"]).total_tasks
            } for r in results
        ], key=lambda x: x["created_at"], reverse=True)

# Singleton
_storage_service_instance = None

def get_storage_service(db_path: Optional[str] = None) -> StorageService:
    global _storage_service_instance
    if _storage_service_instance is None:
        if db_path is None:
            from app.config import get_config
            db_path = get_config().TINYDB_PATH
        _storage_service_instance = StorageService(db_path)
    return _storage_service_instance