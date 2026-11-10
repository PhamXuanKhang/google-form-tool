"""Prefill link generator (TIP-003).

Convert a :class:`~app.models.Form` and response dictionaries into Google Forms
prefill URLs. The generated URLs can be opened directly in a browser; Google
Forms will pre-populate fields whose ``entry.<id>`` parameters appear in the
query string.

Mapping rules:
    * Response keys may be either the raw question id (e.g. ``"123456789"``) or
      the full entry parameter (e.g. ``"entry.123456789"``).
    * Mapping is driven by :meth:`Question.get_entry_param`, the canonical
      source of prefill metadata since TIP-002.

Encoding rules:
    * Single-valued answers (text, date, time, email, multiple choice,
      dropdown, linear scale) become one query parameter.
    * List-valued answers (checkbox) emit one query parameter per element with
      the same ``entry.<id>`` key.
    * Empty strings, ``None``, and empty lists are skipped.
    * Nested objects raise :class:`ValueError`.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import quote_plus, urlsplit, urlunsplit

from app.models import Form, Question
from app.logging_config import logger


class PrefillLinkGenerator:
    """Build Google Forms prefill URLs from configured response dictionaries."""

    def __init__(self, form: Form):
        self.form = form
        self._base_url = self._normalize_base_url(str(form.url))
        # Map every accepted lookup key (raw question_id and full entry_id) to
        # the canonical "entry.<id>" parameter name.
        self._entry_lookup: Dict[str, str] = {}
        # Keep insertion order for deterministic URL output.
        self._questions_in_order: List[Question] = []
        for page in form.response_config.pages if form.response_config else []:
            for question in page.questions or []:
                entry_param = question.get_entry_param()
                if not entry_param:
                    continue
                self._questions_in_order.append(question)
                self._entry_lookup[question.question_id] = entry_param
                self._entry_lookup[entry_param] = entry_param

    # ------------------------------------------------------------------ public

    def build_prefill_url(self, responses: Dict[str, Any]) -> str:
        """Return one prefill URL for the given response dictionary."""
        params = self._build_params(responses)
        return self._compose_url(params)

    def build_prefill_urls(self, responses_list: List[Dict[str, Any]]) -> List[str]:
        """Return one prefill URL per response dictionary."""
        return [self.build_prefill_url(r) for r in responses_list]

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        """Normalize the stored form URL to a Google Forms ``/viewform`` URL.

        Match the old prefill-link script: keep only the form path and start
        every generated link from ``?usp=pp_url``.
        """
        parts = urlsplit(url)
        path = parts.path or ""
        for suffix in ("/formResponse", "/viewform"):
            if path.endswith(suffix):
                path = path[: -len(suffix)]
                break
        path = path.rstrip("/") + "/viewform"
        return urlunsplit((parts.scheme, parts.netloc, path, "usp=pp_url", ""))

    def _resolve_entry(self, key: str) -> Tuple[str, Question]:
        entry_param = self._entry_lookup.get(key)
        if entry_param is None:
            # Allow callers to pass either form. If the user passed an
            # entry-prefixed key we never extracted, fall through to a clear
            # error rather than silently dropping it.
            raise ValueError(
                f"No entry mapping for response key '{key}'. "
                "Re-extract the form so questions have entry_id metadata."
            )
        # Find the originating question for richer error messages downstream.
        for q in self._questions_in_order:
            if q.get_entry_param() == entry_param:
                return entry_param, q
        # Should not happen — _entry_lookup was built from these same questions.
        raise ValueError(f"Internal mapping inconsistency for key '{key}'")

    def _build_params(self, responses: Dict[str, Any]) -> List[Tuple[str, str]]:
        params: List[Tuple[str, str]] = []
        for raw_key, value in responses.items():
            if value is None or value == "" or value == []:
                continue
            entry_param, question = self._resolve_entry(raw_key)
            for encoded in self._encode_value(value, question):
                params.append((entry_param, encoded))
        return params

    @staticmethod
    def _encode_value(value: Any, question: Question) -> Iterable[str]:
        """Yield string values for ``value``; one yield per query parameter."""
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None or item == "":
                    continue
                if isinstance(item, (list, tuple, dict)):
                    raise ValueError(
                        f"Nested value in answer for question "
                        f"'{question.question_id}' is not supported"
                    )
                yield PrefillLinkGenerator._stringify(item)
            return
        if isinstance(value, dict):
            raise ValueError(
                f"Object value in answer for question "
                f"'{question.question_id}' is not supported"
            )
        yield PrefillLinkGenerator._stringify(value)

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, bool):
            # bool is an int subclass; stringify before the int branch.
            return "true" if value else "false"
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.strftime("%H:%M")
        return str(value)

    def _compose_url(self, params: List[Tuple[str, str]]) -> str:
        encoded_params = []
        for entry_param, value in params:
            if value.startswith("__other_option__&"):
                encoded_params.append(f"{entry_param}=__other_option__")
                encoded_params.append(value.split("&", 1)[1])
            else:
                encoded_params.append(f"{entry_param}={quote_plus(value)}")

        suffix = f"&{'&'.join(encoded_params)}" if encoded_params else ""
        url = f"{self._base_url}{suffix}"
        logger.debug("Built prefill URL with %d answer params", len(params))
        return url
