from typing import Dict, Any, List, Optional
from tinydb import TinyDB, Query, where
from tinydb.table import Document
from app.models import FormData, ResponseConfig, Form
from logging import getLogger

logger = getLogger(__name__)

# TODO: Check again
class StorageService:
    """
    Service for storing and retrieving data using TinyDB.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[TinyDB] = None
        self.query = Query()


    def __enter__(self):
        """
        Open the TinyDB database connection.
        """
        self.db = TinyDB(self.db_path)
        logger.info("StorageService opened DB connection.")
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the TinyDB database connection on exit.
        """
        if self.db is not None:
            self.db.close()
            logger.info("StorageService closed DB connection.")
        
    

    #---------------------------------------------#
    #------------------- READ --------------------#
    #---------------------------------------------#
    def get_all_forms_summary(self) -> List[dict]:
        """
        Get summary information of all stored forms.

        Returns:
            List[dict]: A list of summaries with basic form metadata.
        """
        try:
            forms = self.db.all()
            summaries = [
                {
                    "id": form["id"],
                    "title": form["title"],
                    "description": form["description"],
                    "url": form["url"],
                    "created_at": form["created_at"],
                    "last_used": form["last_used"],
                    "response_config": True if form["response_config"] else False,
                    "total_fill": len(form["submissions"]) if form["submissions"] else 0
                }
                for form in forms
            ]
            logger.info(f"Retrieved {len(summaries)} forms summary")
            return summaries
        except Exception as e:
            logger.error(f"Error retrieving forms summary: {e}")
            raise


    def _load_form(self, form_id: str) -> Optional[Form]:
        """
        Load a Form object from the database by its ID.

        Args:
            db_path (str): The path to the json file.
        """
        try:
            form_data = self.db.search(self.query.id == form_id)
            if form_data:
                form = Form(**form_data[0])
                logger.info(f"Loaded form: {form_id}")
                return form
            else:
                logger.warning(f"Form not found: {form_id}")
        except ValidationError as e:
            logger.error(f"Validation error for form_id {form_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading form {form_id}: {e}")
            raise


    def get_form_by_url(self, url: str) -> Optional[Form]:
        """
        Get a form by its URL.

        Args:
            url (str): The URL of the form.

        Returns:
            Optional[Form]: The form or None.
        """
        form = self._load_form(Form.get_id_from_url(url))
        if form:
            logger.info(f"Retrieved form by URL: {url}")
            return form
        else:
            return None


    def get_form_response_config(self, form_id: str) -> Optional[ResponseConfig]:
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

    def delete_submission(self, form_id: str, submission_id: str) -> bool:
        """
        Delete a specific submission from a form.

        Args:
            form_id (str): ID of the form.
            submission_id (str): ID of the submission to delete.

        Returns:
            bool: True if deleted, False otherwise.
        """
        form = self._load_form(form_id)
        if form:
            form.submissions = [s for s in form.submissions if s.submission_id != submission_id]
            self.db.update(self._dump(form), self.query.id == form_id)
            logger.info(f"Deleted submission from form: {form_id}")
            return True
        else:
            return False
