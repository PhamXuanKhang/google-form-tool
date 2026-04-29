"""
AI Responder Module

Uses Google Gemini API to generate context-aware responses for form questions.
API key is provided by user via UI (not from env) for flexibility.
"""
import json
from typing import Optional, Dict, Any, List
from app.models import Question
from app.logging_config import logger

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed. AI responses will not be available.")


class AIResponder:
    """
    Generate AI-powered responses for form questions using Google Gemini.

    The API key is provided at runtime (not from env) to allow users to
    use their own keys without server-side configuration.
    """

    def __init__(self, api_key: str):
        """
        Initialize the AI responder with a Gemini API key.

        Args:
            api_key (str): Google Gemini API key from user input
        """
        if not GENAI_AVAILABLE:
            raise RuntimeError("google-generativeai package is not installed")

        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self._cache: Dict[str, str] = {}

    def generate_response(self, question: Question, context: Optional[str] = None) -> str:
        """
        Generate a contextual response for a single question.

        Args:
            question (Question): The question to generate a response for
            context (str, optional): Additional context about the form

        Returns:
            str: Generated response appropriate for the question type
        """
        cache_key = f"{question.question_id}:{question.text}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = self._build_prompt(question, context)

        try:
            response = self.model.generate_content(prompt)
            answer = self._extract_answer(response.text, question)
            self._cache[cache_key] = answer
            logger.info(f"AI generated response for question: {question.question_id}")
            return answer
        except Exception as e:
            logger.error(f"AI generation failed for {question.question_id}: {e}")
            return self._fallback_response(question)

    def generate_responses_batch(
        self, questions: List[Question], context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate responses for multiple questions.

        Args:
            questions (List[Question]): List of questions
            context (str, optional): Form context

        Returns:
            Dict[str, Any]: Map of question_id to generated response
        """
        responses = {}
        for question in questions:
            responses[question.question_id] = self.generate_response(question, context)
        return responses

    def _build_prompt(self, question: Question, context: Optional[str]) -> str:
        """Build the prompt for Gemini based on question type."""
        q_type = question.type
        q_text = question.text

        base_prompt = f"""You are filling out a form. Generate a realistic, appropriate response.

Question: {q_text}
Question Type: {q_type}
"""

        if context:
            base_prompt += f"\nForm Context: {context}\n"

        if q_type in ["multiple_choice", "dropdown"]:
            options = [opt.text for opt in (question.answer_config.options or [])]
            base_prompt += f"\nAvailable options: {options}"
            base_prompt += "\nRespond with ONLY the exact text of one option, nothing else."

        elif q_type == "checkbox":
            options = [opt.text for opt in (question.answer_config.options or [])]
            base_prompt += f"\nAvailable options: {options}"
            base_prompt += "\nRespond with a JSON array of selected option texts. Example: [\"Option1\", \"Option2\"]"

        elif q_type == "linear_scale":
            base_prompt += "\nRespond with ONLY a number (e.g., 1, 2, 3, 4, or 5)."

        elif q_type == "input_email":
            base_prompt += "\nRespond with ONLY a realistic email address."

        elif q_type == "date":
            base_prompt += "\nRespond with ONLY a date in YYYY-MM-DD format."

        elif q_type == "time":
            base_prompt += "\nRespond with ONLY a time in HH:MM format."

        elif q_type in ["input_text", "textarea"]:
            if q_type == "textarea":
                base_prompt += "\nProvide a thoughtful paragraph response (2-4 sentences)."
            else:
                base_prompt += "\nProvide a concise response (1-10 words)."

        base_prompt += "\n\nYour response:"

        return base_prompt

    def _extract_answer(self, raw_response: str, question: Question) -> Any:
        """Extract and format the answer from AI response."""
        answer = raw_response.strip()

        if question.type == "checkbox":
            try:
                parsed = json.loads(answer)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [answer]

        elif question.type == "linear_scale":
            try:
                num = int(''.join(filter(str.isdigit, answer[:5])))
                return max(1, min(5, num))
            except (ValueError, IndexError):
                return 3

        return answer

    def _fallback_response(self, question: Question) -> Any:
        """Provide fallback response when AI fails."""
        q_type = question.type

        if q_type in ["multiple_choice", "dropdown"]:
            if question.answer_config and question.answer_config.options:
                return question.answer_config.options[0].text
            return "Option 1"

        elif q_type == "checkbox":
            if question.answer_config and question.answer_config.options:
                return [question.answer_config.options[0].text]
            return ["Option 1"]

        elif q_type == "linear_scale":
            return 3

        elif q_type == "input_email":
            return "user@example.com"

        elif q_type == "date":
            return "2025-01-01"

        elif q_type == "time":
            return "12:00"

        elif q_type == "textarea":
            return "This is a sample response generated as a fallback."

        return "Sample response"

    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple request.

        Returns:
            bool: True if key is valid, False otherwise
        """
        try:
            response = self.model.generate_content("Say 'OK'")
            return bool(response.text)
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False


def is_ai_available() -> bool:
    """Check if AI functionality is available (package installed)."""
    return GENAI_AVAILABLE
