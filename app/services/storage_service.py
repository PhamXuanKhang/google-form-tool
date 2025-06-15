from typing import Optional, List
from tinydb import TinyDB, Query
from pydantic import ValidationError
from app.models import Form, ResponseConfig, Submission
from app.logging_config import logger


class StorageService:
    """
    Service for storing and managing Form data using TinyDB.

    This service handles operations such as saving, updating, deleting, and retrieving forms, response configurations, and submissions. It uses Pydantic models (Form, ResponseConfig, Submission) and stores them as JSON.

    Context management is supported using `with` syntax to ensure database is properly opened and closed.

    Attributes:
        db_path (str): Path to the TinyDB JSON file.
        db (TinyDB): Database instance (opened in context).
        query (Query): Query helper for TinyDB operations.
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
            form_id (str): The form ID to look up.

        Returns:
            Optional[Form]: The loaded Form or None if not found.
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


    def get_form_response_config(self, form_id: str) -> Optional[ResponseConfig]:
        """
        Get the response configuration of a form.

        Args:
            form_id (str): The ID of the form.

        Returns:
            Optional[ResponseConfig]: The form's response config or None.
        """
        form = self._load_form(form_id)
        if form:
            logger.info(f"Retrieved response config for form: {form_id}")
            return form.response_config
        else:
            return None


    def get_submission(self, form_id: str) -> Optional[List[Submission]]:
        """
        Get all submissions of a form.

        Args:
            form_id (str): The form ID.

        Returns:
            Optional[List[Submission]]: A list of submissions or None.
        """
        form = self._load_form(form_id)
        if form:
            logger.info(f"Retrieved submission for form: {form_id}")
            return form.submissions
        else:
            return None



    #---------------------------------------------#
    #-------------- CREATE + UPDATE --------------#
    #---------------------------------------------#
    def _dump(self, model):
        """
        Serialize a Pydantic model to JSON-compatible dict.

        Args:
            model (BaseModel): A Pydantic model.

        Returns:
            dict: Serialized dictionary.
        """
        return model.model_dump(mode='json')
    

    def save_form(self, form: Form) -> bool:
        """
        Save or update a form in the database.

        Args:
            form (Form): The form to save.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            self.db.upsert(self._dump(form), self.query.id == form.id)
            logger.info(f"Saved form: {form.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving form {form.id}: {e}")
            return False


    def update_response_config(self, form_id: str, response_config: ResponseConfig) -> bool:
        """
        Update the response configuration of a form.

        Args:
            form_id (str): ID of the form.
            response_config (ResponseConfig): New response config.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        form = self._load_form(form_id)
        if form:
            form.response_config = response_config
            self.db.update(self._dump(form), self.query.id == form_id)
            logger.info(f"Updated response config for form: {form_id}")
            return True
        else:
            return False


    def add_submission(self, form_id: str, submission: Submission) -> bool:
        """
        Add a submission to the form.

        Args:
            form_id (str): ID of the form.
            submission (Submission): Submission to add.

        Returns:
            bool: True if added successfully, False otherwise.
        """
        form = self._load_form(form_id)
        if form:
            if form.submissions:
                form.submissions.append(submission)
            else:
                form.submissions = [submission]
            self.db.update(self._dump(form), self.query.id == form_id)
            logger.info(f"Added submission to form: {form_id}")
            return True
        else:
            return False



    #---------------------------------------------#
    #------------------ DELETE -------------------#
    #---------------------------------------------#
    def delete_form(self, form_id: str) -> bool:
        """
        Delete a form from the database.

        Args:
            form_id (str): ID of the form to delete.

        Returns:
            bool: True if deleted, False otherwise.
        """
        try:
            self.db.remove(self.query.id == form_id)
            logger.info(f"Deleted form: {form_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting form {form_id}: {e}")
            return False
        

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