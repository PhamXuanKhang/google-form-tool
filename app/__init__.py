"""
Google Form Automation Tool application package.

Importing ``app`` stays light: the Flask factory (``app.factory``) and the
models are loaded on first use, so processes that only need part of the
package, such as the MCP server, do not import Flask or Selenium.
``from app import create_app, Form`` keeps working.
"""

__version__ = "2.0.0"

_FACTORY_NAMES = {"create_app", "get_locale", "SUPPORTED_LANGUAGES", "BABEL_AVAILABLE"}
_MODEL_NAMES = {
    "AnswerConfig", "AnswerOption", "CopyOperation", "CopyPlan", "CopyResult", "CopyWarning",
    "FormData", "Form", "Page", "Question", "ResponseConfig", "Submission",
}


def __getattr__(name):
    if name in _FACTORY_NAMES:
        from app import factory
        return getattr(factory, name)
    if name in _MODEL_NAMES:
        from app import models
        return getattr(models, name)
    raise AttributeError(f"module 'app' has no attribute {name!r}")
