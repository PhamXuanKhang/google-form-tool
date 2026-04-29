"""
Form Processor Module

This module handles the processing of form data, including generating automated responses
and preparing data for submission.
"""
import csv
import json
import random
import string
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.models import Form, Question, AnswerConfig, AnswerOption
from app.logging_config import logger


class FormProcessor:
    """
    Process form data and generate responses for different question types.
    
    This class handles:
    1. Loading data from external sources
    2. Generating random or AI-powered responses
    3. Mapping external data to form fields
    4. Validating and formatting responses
    """
    
    def __init__(self, form: Form):
        """
        Initialize the FormProcessor with a form object.
        
        Args:
            form (Form): The form to process
        """
        self.form = form
        self.response_data = {}
    
    def load_data_from_file(
        self, file_path: str, mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Load data from an external file and map it to form fields.

        Supported formats:
        - CSV: Each row becomes one submission's responses
        - JSON: Expects a list of objects, each object is one submission
        - XLSX: First worksheet, first row as headers, each subsequent row as responses

        Args:
            file_path (str): Path to the data file (CSV, JSON, or XLSX)
            mapping (Dict[str, str], optional): Mapping of file columns to question IDs.
                                               If None, assumes column names match question IDs.

        Returns:
            List[Dict[str, Any]]: List of response dictionaries, each representing
                                  one set of form responses (question_id -> answer).

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file format is unsupported or data is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        logger.info(f"Loading data from file: {file_path} (format: {suffix})")

        if suffix == ".csv":
            return self._load_csv(path, mapping)
        elif suffix == ".json":
            return self._load_json(path, mapping)
        elif suffix == ".xlsx":
            return self._load_xlsx(path, mapping)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .csv, .json, or .xlsx")

    def _load_csv(
        self, path: Path, mapping: Optional[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Load responses from a CSV file."""
        responses_list = []

        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                responses = {}
                for col_name, value in row.items():
                    if not col_name or not value:
                        continue
                    question_id = mapping.get(col_name, col_name) if mapping else col_name
                    responses[question_id] = self._parse_value(value)
                if responses:
                    responses_list.append(responses)

        logger.info(f"Loaded {len(responses_list)} response sets from CSV")
        return responses_list

    def _load_json(
        self, path: Path, mapping: Optional[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Load responses from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        responses_list = []
        for item in data:
            if not isinstance(item, dict):
                continue
            responses = {}
            for col_name, value in item.items():
                if value is None:
                    continue
                question_id = mapping.get(col_name, col_name) if mapping else col_name
                responses[question_id] = value
            if responses:
                responses_list.append(responses)

        logger.info(f"Loaded {len(responses_list)} response sets from JSON")
        return responses_list

    def _load_xlsx(
        self, path: Path, mapping: Optional[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Load responses from the first worksheet in an XLSX file."""
        try:
            from openpyxl import load_workbook
        except ImportError as e:
            raise ValueError("Excel import requires openpyxl to be installed.") from e

        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            worksheet = workbook.worksheets[0]
            rows = worksheet.iter_rows(values_only=True)
            headers = next(rows, None)

            if not headers:
                return []

            responses_list = []
            for row in rows:
                responses = {}
                for col_name, value in zip(headers, row):
                    if col_name is None or value is None:
                        continue
                    if isinstance(value, str) and not value.strip():
                        continue

                    col_key = str(col_name).strip()
                    if not col_key:
                        continue

                    question_id = mapping.get(col_key, col_key) if mapping else col_key
                    responses[question_id] = self._normalize_excel_value(value)

                if responses:
                    responses_list.append(responses)

            logger.info(f"Loaded {len(responses_list)} response sets from XLSX")
            return responses_list
        finally:
            workbook.close()

    def _normalize_excel_value(self, value: Any) -> Any:
        """Normalize Excel-only values while preserving useful primitive types."""
        if isinstance(value, datetime):
            return value.isoformat(sep=" ")
        if isinstance(value, (date, time)):
            return value.isoformat()
        return value

    def _parse_value(self, value: str) -> Any:
        """Parse a string value into appropriate type."""
        value = value.strip()
        if not value:
            return None
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False
        if "," in value and not value.startswith('"'):
            return [v.strip() for v in value.split(",")]
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value
    
    def generate_random_responses(self, fill_percentage: int = 100) -> Dict[str, Any]:
        """
        Generate random responses for all questions in the form.
        
        Args:
            fill_percentage (int): Percentage of questions to fill (0-100)
            
        Returns:
            Dict[str, Any]: Generated responses mapped to question IDs
        """
        responses = {}
        
        if not self.form.response_config or not self.form.response_config.pages:
            logger.error("Form has no response configuration or pages")
            return {}
        
        for page in self.form.response_config.pages:
            if not page.questions:
                continue
                
            for question in page.questions:
                if not self._should_fill_question(question, fill_percentage):
                    continue
                    
                response = self._generate_response_for_question(question)
                if response is not None:
                    responses[question.question_id] = response
        
        logger.info(f"Generated {len(responses)} random responses")
        return responses
    
    def _generate_response_for_question(self, question: Question) -> Any:
        """
        Generate a response for a specific question based on its type.
        
        Args:
            question (Question): The question to generate a response for
            
        Returns:
            Any: Generated response appropriate for the question type
        """
        q_type = question.type
        
        if q_type in ["input_text", "input_email", "textarea", "date", "time"]:
            configured_answer = self._select_configured_answer(question)
            if configured_answer is not None:
                return configured_answer

        if q_type == "input_text":
            return self._generate_text_response(5, 20)
        
        elif q_type == "input_email":
            return self._generate_email()
        
        elif q_type == "textarea":
            return self._generate_text_response(20, 100)
        
        elif q_type in ["multiple_choice", "dropdown", "linear_scale"]:
            configured_option = self._select_weighted_option(question)
            if configured_option is not None:
                return configured_option
            if q_type == "linear_scale":
                return self._generate_scale_response()
            return self._select_random_option(question)
        
        elif q_type == "checkbox":
            return self._select_multiple_options(question)
        
        elif q_type == "date":
            return self._generate_date()
        
        elif q_type == "time":
            return self._generate_time()
        
        elif q_type == "rank":
            return self._generate_rank_response(question)
        
        else:
            logger.warning(f"Unsupported question type: {q_type}")
            return None

    def _should_fill_question(self, question: Question, global_fill_percentage: int) -> bool:
        """Return whether a question should be answered for this generated response."""
        question_fill = None
        if question.answer_config and question.answer_config.fill_percentage is not None:
            question_fill = question.answer_config.fill_percentage

        fill_percentage = question_fill if question_fill is not None else global_fill_percentage
        fill_percentage = max(0, min(100, float(fill_percentage)))

        if fill_percentage <= 0:
            return False
        if fill_percentage >= 100:
            return True
        return random.random() * 100 < fill_percentage

    def _select_configured_answer(self, question: Question) -> Optional[Any]:
        """Select from user-configured text-like answers when available."""
        if not question.answer_config or not question.answer_config.answers:
            return None

        answers = [answer for answer in question.answer_config.answers if answer not in (None, "")]
        if not answers:
            return None

        return random.choice(answers)

    def _select_weighted_option(self, question: Question) -> Optional[str]:
        """Select a single option using configured percentages when available."""
        if not question.answer_config or not question.answer_config.options:
            return None

        options = question.answer_config.options
        weights = [max(0, float(option.percentage or 0)) for option in options]
        if sum(weights) <= 0:
            return random.choice([option.text for option in options])

        return random.choices(options, weights=weights, k=1)[0].text
    
    def _generate_text_response(self, min_length: int, max_length: int) -> str:
        """Generate a random text string of specified length"""
        length = random.randint(min_length, max_length)
        words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 
                'adipiscing', 'elit', 'sed', 'do', 'eiusmod', 'tempor', 
                'incididunt', 'ut', 'labore', 'et', 'dolore', 'magna', 'aliqua']
        
        return ' '.join(random.choices(words, k=length // 3))
    
    def _generate_email(self) -> str:
        """Generate a random email address"""
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com']
        username_length = random.randint(5, 10)
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
        domain = random.choice(domains)
        
        return f"{username}@{domain}"
    
    def _select_random_option(self, question: Question) -> str:
        """Select a random option from a multiple choice or dropdown question"""
        if not question.answer_config or not question.answer_config.options:
            return "Option 1"  # Default fallback
        
        return random.choice([opt.text for opt in question.answer_config.options])
    
    def _select_multiple_options(self, question: Question) -> List[str]:
        """Select multiple random options for a checkbox question"""
        if not question.answer_config or not question.answer_config.options:
            return ["Option 1"]  # Default fallback

        configured_options = question.answer_config.options
        weights = [max(0, float(option.percentage or 0)) for option in configured_options]
        if any(weight > 0 for weight in weights):
            return [
                option.text
                for option, weight in zip(configured_options, weights)
                if random.random() * 100 < weight
            ]
        
        options = [opt.text for opt in configured_options]
        # Select 1 to all options
        num_to_select = random.randint(1, len(options))
        
        return random.sample(options, num_to_select)
    
    def _generate_scale_response(self) -> int:
        """Generate a random scale response (1-5)"""
        return random.randint(1, 5)
    
    def _generate_date(self) -> str:
        """Generate a random date in YYYY-MM-DD format"""
        year = random.randint(2020, 2025)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Simplified to avoid month length issues
        
        return f"{year}-{month:02d}-{day:02d}"
    
    def _generate_time(self) -> str:
        """Generate a random time in HH:MM format"""
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        
        return f"{hour:02d}:{minute:02d}"
    
    def _generate_rank_response(self, question: Question) -> List[str]:
        """Generate a random ranking of options"""
        if not question.answer_config or not question.answer_config.options:
            return ["Rank 1", "Rank 2", "Rank 3"]  # Default fallback
        
        options = [opt.text for opt in question.answer_config.options]
        random.shuffle(options)
        
        return options
    
    def apply_user_edits(self, edits: Dict[str, Any]) -> None:
        """
        Apply user edits to the response configuration.
        
        Args:
            edits (Dict[str, Any]): Dictionary of edits keyed by question ID
        """
        if not self.form.response_config or not self.form.response_config.pages:
            logger.error("Cannot apply edits: Form has no response configuration")
            return
        
        for page in self.form.response_config.pages:
            if not page.questions:
                continue
                
            for question in page.questions:
                if question.question_id in edits:
                    self._apply_edit_to_question(question, edits[question.question_id])
        
        logger.info(f"Applied {len(edits)} user edits to form configuration")
    
    def _apply_edit_to_question(self, question: Question, edit: Dict[str, Any]) -> None:
        """
        Apply an edit to a specific question's answer configuration.
        
        Args:
            question (Question): The question to edit
            edit (Dict[str, Any]): The edit data
        """
        if not question.answer_config:
            question.answer_config = AnswerConfig(fill_percentage=0, answers=[], options=None)
        
        # Update fill percentage if provided
        if 'fill_percentage' in edit:
            question.answer_config.fill_percentage = edit['fill_percentage']
        
        # Update answers if provided
        if 'answers' in edit:
            question.answer_config.answers = edit['answers']
        
        # Update options if provided
        if 'options' in edit and question.answer_config.options:
            # Match options by text and update percentages
            option_map = {opt.text: opt for opt in question.answer_config.options}
            for option_edit in edit['options']:
                if option_edit['text'] in option_map:
                    option_map[option_edit['text']].percentage = option_edit['percentage']
