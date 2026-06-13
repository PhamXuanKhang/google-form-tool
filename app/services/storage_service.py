"""Storage service for TinyDB operations on Form data."""

import threading
from typing import List, Optional
from tinydb import TinyDB, Query
from pydantic import ValidationError
from app.models import Form, ResponseConfig, Submission
from logging import getLogger

logger = getLogger(__name__)

_DB_WRITE_LOCK = threading.RLock()


class StorageService:
    """
    Service for storing and retrieving Form data using TinyDB.

    Uses context manager pattern for safe DB connection handling.
    All forms are stored in a single table with deterministic IDs based on URL.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[TinyDB] = None
        self.query = Query()

    def __enter__(self):
        """Open the TinyDB database connection."""
        self.db = TinyDB(self.db_path)
        logger.info("StorageService opened DB connection.")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the TinyDB database connection on exit."""
        if self.db is not None:
            self.db.close()
            logger.info("StorageService closed DB connection.")

    def _dump(self, form: Form) -> dict:
        """Serialize Form to dict for TinyDB storage."""
        return form.model_dump(mode="json")

    # -------------------- READ --------------------

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
                    "response_config": True if form.get("response_config") else False,
                    "total_fill": len(form.get("submissions") or [])
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
            form_id (str): The form ID to search for.

        Returns:
            Optional[Form]: The Form object or None if not found.
        """
        try:
            form_data = self.db.search(self.query.id == form_id)
            if form_data:
                form = Form(**form_data[0])
                logger.info(f"Loaded form: {form_id}")
                return form
            else:
                logger.warning(f"Form not found: {form_id}")
                return None
        except ValidationError as e:
            logger.error(f"Validation error for form_id {form_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading form {form_id}: {e}")
            raise

    def get_form_by_id(self, form_id: str) -> Optional[Form]:
        """
        Get a form by its ID.

        Args:
            form_id (str): The form ID.

        Returns:
            Optional[Form]: The form or None.
        """
        return self._load_form(form_id)

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

    def get_form_response_config(self, form_id: str) -> Optional[ResponseConfig]:
        """
        Get the response configuration of a form.

        Args:
            form_id (str): The form ID.

        Returns:
            Optional[ResponseConfig]: The response config or None if form not found.
        """
        form = self._load_form(form_id)
        if form:
            logger.info(f"Retrieved response config for form: {form_id}")
            return form.response_config
        return None

    def get_submission(self, form_id: str) -> Optional[List[Submission]]:
        """
        Get all submissions for a form.

        Args:
            form_id (str): The form ID.

        Returns:
            Optional[List[Submission]]: List of submissions or None if form not found.
        """
        form = self._load_form(form_id)
        if form:
            logger.info(f"Retrieved submission for form: {form_id}")
            return form.submissions or []
        return None

    # -------------------- WRITE --------------------

    def save_form(self, form: Form) -> bool:
        """
        Save or update a form in the database.

        Args:
            form (Form): The form to save.

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        try:
            with _DB_WRITE_LOCK:
                self.db.upsert(self._dump(form), self.query.id == form.id)
            logger.info(f"Saved form: {form.id}")
            return True
        except Exception as e:
            logger.error(f"Error saving form {form.id}: {e}")
            return False

    def update_response_config(self, form_id: str, config: ResponseConfig) -> bool:
        """
        Update the response configuration of a form.

        Args:
            form_id (str): The form ID.
            config (ResponseConfig): The new response configuration.

        Returns:
            bool: True if updated, False if form not found.
        """
        with _DB_WRITE_LOCK:
            form = self._load_form(form_id)
            if form:
                form.response_config = config
                self.db.update(self._dump(form), self.query.id == form_id)
                logger.info(f"Updated response config for form: {form_id}")
                return True
        return False

    def add_submission(self, form_id: str, submission: Submission) -> bool:
        """
        Add a submission record to a form.

        Args:
            form_id (str): The form ID.
            submission (Submission): The submission to add.

        Returns:
            bool: True if added, False if form not found.
        """
        with _DB_WRITE_LOCK:
            form = self._load_form(form_id)
            if form:
                if form.submissions is None:
                    form.submissions = []
                form.submissions.append(submission)
                self.db.update(self._dump(form), self.query.id == form_id)
                logger.info(f"Added submission to form: {form_id}")
                return True
        return False

    # -------------------- DELETE --------------------

    def delete_form(self, form_id: str) -> bool:
        """
        Delete a form from the database.

        Args:
            form_id (str): The form ID to delete.

        Returns:
            bool: True (TinyDB remove returns empty list if no match).
        """
        with _DB_WRITE_LOCK:
            self.db.remove(self.query.id == form_id)
        logger.info(f"Deleted form: {form_id}")
        return True

    def delete_submission(self, form_id: str, submission_id: str) -> bool:
        """
        Delete a specific submission from a form.

        Args:
            form_id (str): ID of the form.
            submission_id (str): ID of the submission to delete.

        Returns:
            bool: True if form found, False otherwise.
        """
        with _DB_WRITE_LOCK:
            form = self._load_form(form_id)
            if form:
                if form.submissions:
                    form.submissions = [
                        s for s in form.submissions if s.submission_id != submission_id
                    ]
                self.db.update(self._dump(form), self.query.id == form_id)
                logger.info(f"Deleted submission from form: {form_id}")
                return True
        return False
