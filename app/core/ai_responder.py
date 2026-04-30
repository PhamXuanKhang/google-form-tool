"""
AI Responder Module

Uses Google Gemini API to generate context-aware responses for form questions.
API key is provided by user via UI (not from env) for flexibility.
"""
import json
from typing import Optional, Dict, Any, List
from app.models import Question
from config import Config
from app.logging_config import logger

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # sentinel so monkeypatch targets still resolve
    GENAI_AVAILABLE = False
    logger.warning("google-genai not installed. AI responses will not be available.")


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
            raise RuntimeError("google-genai package is not installed")

        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model_name = self._resolve_model_name(self.client, Config.GEMINI_MODEL)
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
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
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

    def generate_text_variations(
        self,
        question: Question,
        count: int,
        context: Optional[str] = None,
    ) -> List[str]:
        """
        Generate ``count`` distinct text answers for one text-like question.

        Used by the inline AI option on each text/textarea question card
        (TIP-006). Bypasses ``self._cache`` so repeated clicks return fresh
        variations rather than the previously cached single answer.

        Falls back to ``count`` copies of ``_fallback_response`` if Gemini
        returns malformed output.
        """
        if count <= 0:
            return []
        if question.type not in ("input_text", "textarea"):
            raise ValueError(
                f"AI text variations are only supported for input_text/textarea, "
                f"got '{question.type}'"
            )

        base = self._build_prompt(question, context).rstrip()
        if base.endswith("Your response:"):
            base = base[: -len("Your response:")].rstrip()

        prompt = (
            f"{base}\n\n"
            f"Generate {count} distinct realistic answers as a JSON array of "
            f'strings. Example: ["answer one", "answer two"]. Respond with ONLY '
            f"the JSON array, no extra commentary.\n\nYour response:"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt
            )
            answers = self._parse_text_array(response.text)
            if answers:
                # Pad/truncate to the exact count requested.
                if len(answers) < count:
                    answers = answers + [
                        self._fallback_response(question)
                        for _ in range(count - len(answers))
                    ]
                return [str(a) for a in answers[:count]]
        except Exception as e:
            logger.error(
                f"AI text variation generation failed for "
                f"{question.question_id}: {e}"
            )

        return [str(self._fallback_response(question)) for _ in range(count)]

    @staticmethod
    def _parse_text_array(text: str) -> Optional[List[str]]:
        """Best-effort parser: accept a JSON array, possibly surrounded by prose."""
        if not text:
            return None
        candidate = text.strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, list) and data:
                return [str(x) for x in data]
        except (json.JSONDecodeError, ValueError):
            pass

        import re

        match = re.search(r"\[.*\]", candidate, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list) and data:
                    return [str(x) for x in data]
            except (json.JSONDecodeError, ValueError):
                pass
        return None

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
            response = self.client.models.generate_content(
                model=self.model_name, contents="Say 'OK'"
            )
            return bool(response.text)
        except Exception as e:
            logger.error("API key validation failed: %s", type(e).__name__)
            return False

    def _resolve_model_name(self, client, preferred: Optional[str]) -> str:
        models = self._list_models_safe(client)
        preferred = preferred.strip() if isinstance(preferred, str) and preferred.strip() else None
        if models:
            compatible = [
                model for model in models
                if self._supports_generate_content(model)
            ]
            if not compatible:
                raise ModelResolutionError(
                    "No Gemini model supports generateContent for this API key."
                )
            if preferred and any(model.name == preferred for model in compatible):
                return preferred
            fallback = self._pick_fallback_model(compatible)
            if preferred and fallback != preferred:
                logger.warning(
                    "Configured Gemini model '%s' unavailable; falling back to '%s'.",
                    preferred,
                    fallback,
                )
            return fallback

        # Model listing unavailable: fall back to preferred or a default.
        return preferred or "gemini-2.0-flash"

    @staticmethod
    def _supports_generate_content(model: Any) -> bool:
        methods = getattr(model, "supported_generation_methods", None) or []
        actions = getattr(model, "supported_actions", None) or []
        return "generateContent" in methods or "generateContent" in actions

    @staticmethod
    def _pick_fallback_model(models: List[Any]) -> str:
        def score(name: str) -> int:
            name = name.lower()
            if "flash" in name:
                return 3
            if "pro" in name:
                return 2
            return 1

        sorted_models = sorted(
            models,
            key=lambda m: (score(getattr(m, "name", "")), getattr(m, "name", "")),
            reverse=True,
        )
        return getattr(sorted_models[0], "name", "gemini-1.5-flash")

    @staticmethod
    def _list_models_safe(client) -> Optional[List[Any]]:
        try:
            return list(client.models.list())
        except Exception as e:
            logger.warning("Failed to list Gemini models: %s", type(e).__name__)
            return None


def is_ai_available() -> bool:
    """Check if AI functionality is available (package installed)."""
    return GENAI_AVAILABLE


class ModelResolutionError(RuntimeError):
    """Raised when no compatible Gemini model is available for generation."""
