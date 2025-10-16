"""
Form Processor Module

This module handles the processing of form data, including generating automated responses
and preparing data for submission.
"""
from app.models import Form, Question, AnswerConfig, AnswerOption
from typing import Dict, List, Any, Optional
import random
import string
import datetime
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
    
    def load_data_from_file(self, file_path: str, mapping: Dict[str, str]) -> Dict:
        """
        Load data from an external file and map it to form fields.
        
        Args:
            file_path (str): Path to the data file (CSV, JSON, etc.)
            mapping (Dict[str, str]): Mapping of file columns to form fields
            
        Returns:
            Dict: Processed data mapped to form fields
        """
        # TODO: Implement file loading based on file type
        # For now, return a placeholder
        logger.info(f"Loading data from file: {file_path}")
        return {"data_loaded": True}
    
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
                # Skip some questions based on fill_percentage
                if random.randint(1, 100) > fill_percentage:
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
        
        if q_type == "input_text":
            return self._generate_text_response(5, 20)
        
        elif q_type == "input_email":
            return self._generate_email()
        
        elif q_type == "textarea":
            return self._generate_text_response(20, 100)
        
        elif q_type in ["multiple_choice", "dropdown"]:
            return self._select_random_option(question)
        
        elif q_type == "checkbox":
            return self._select_multiple_options(question)
        
        elif q_type == "linear_scale":
            return self._generate_scale_response()
        
        elif q_type == "date":
            return self._generate_date()
        
        elif q_type == "time":
            return self._generate_time()
        
        elif q_type == "rank":
            return self._generate_rank_response(question)
        
        else:
            logger.warning(f"Unsupported question type: {q_type}")
            return None
    
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
        
        options = [opt.text for opt in question.answer_config.options]
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
