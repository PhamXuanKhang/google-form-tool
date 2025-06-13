from typing import Optional, List
from tinydb import TinyDB, Query
from pydantic import ValidationError
from app.models import Form, ResponseConfig, Submission
from app.logging_config import logger

# TODO: Continue implementation of the StorageService class.
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
        self.db_path = db_path
        self.db: Optional[TinyDB] = None
        self.query = Query()

    def __enter__(self):
        self.db = TinyDB(self.db_path)
        logger.info("StorageService opened DB connection.")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.db is not None:
            self.db.close()
            logger.info("StorageService closed DB connection.")


    def get_all_forms_summary(self) -> List[dict]:
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
                    "total_fill": len(form["submissions"]) if "submissions" in form else 0
                }
                for form in forms
            ]
            logger.info(f"Retrieved {len(summaries)} forms summary")
            return summaries
        except Exception as e:
            logger.error(f"Error retrieving forms summary: {e}")
            raise


    def get_form_response_config(self, form_id: str) -> Optional[ResponseConfig]:
        try:
            form_data = self.db.search(self.query.id == form_id)
            if form_data:
                form = Form(**form_data[0])
                logger.info(f"Retrieved response_config for form_id: {form_id}")
                return form.response_config
            else:
                logger.warning(f"Form not found: {form_id}")
                return None
        except ValidationError as e:
            logger.error(f"Validation error for form_id {form_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving response_config for form_id {form_id}: {e}")
            raise

    def save_form(self, form: Form) -> Optional[str]:
        try:
            self.db.upsert(form.dict(), self.query.id == form.id)
            logger.info(f"Saved form: {form.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving form {form.id}: {e}")
            return False

    def add_submission(self, form_id: str, submission: Submission) -> bool:
        try:
            form_data = self.db.search(self.query.id == form_id)
            if form_data:
                form = Form(**form_data[0])
                form.submissions.append(submission)
                self.db.update(form.dict(), self.query.id == form_id)
                logger.info(f"Added submission {submission.submission_id} to form {form_id}")
                return True
            logger.warning(f"Form not found for submission: {form_id}")
            return False
        except ValidationError as e:
            logger.error(f"Validation error for submission in form_id {form_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding submission to form_id {form_id}: {e}")
            return False