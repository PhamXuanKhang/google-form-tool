"""Form extraction, preview, delete and form-copy routes."""

from urllib.parse import urlparse

from flask import jsonify, request, session

from app.core import FormExtractor
from app.core.driver_manager import get_chrome_binary, get_chromedriver_path
from app.core.form_copier import FormCopier, is_google_form_edit_url
from app.core.form_copy_planner import FormCopyPlanner
from app.core.form_extractor import DriverStartupError, FormExtractionError, FormLoadError
from app.logging_config import logger
from app.routes import bp
from app.routes.health import _runtime_diagnostics
from app.services import get_storage_service
from app.config import Config


def _is_valid_google_forms_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    if url != url.strip():
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (
        parsed.scheme == 'https'
        and parsed.hostname == 'docs.google.com'
        and parsed.path.startswith('/forms/d/')
    )


@bp.route('/forms/delete', methods=['POST'])
def delete_form():
    data = request.get_json(silent=True) or {}
    form_url = data.get('form_url', '')
    if not isinstance(form_url, str) or not form_url.strip():
        return jsonify({"error": "No form URL provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url.strip())
        if not form:
            return jsonify({"error": "Form not found"}), 404
        storage.delete_form(form.id)

    return jsonify({"success": True})


def _is_google_form_url(form_url: str) -> bool:
    return isinstance(form_url, str) and form_url.startswith('https://docs.google.com/forms/')


def _extract_or_load_form(form_url: str):
    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if form:
            return form

        form_extractor = FormExtractor(
            chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
            chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
            headless=True,
        )
        form = form_extractor.extract_form_data(form_url)
        storage.save_form(form)
        return form


@bp.route('/form_copy/extract_source', methods=['POST'])
def form_copy_extract_source():
    data = request.get_json(silent=True) or {}
    form_url = data.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400
    if not _is_google_form_url(form_url):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400

    try:
        form = _extract_or_load_form(form_url)
    except ValueError as e:
        logger.warning(f"Invalid Google Form URL: {form_url}. Details: {str(e)}")
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
    except DriverStartupError as e:
        logger.exception(f"Chrome/ChromeDriver startup failed while extracting source form: {e}")
        return jsonify({
            "error": (
                "Chrome or ChromeDriver could not start. Please check that Chrome is installed, "
                "ChromeDriver is available, and the runtime diagnostics paths are writable."
            ),
            "diagnostics": _runtime_diagnostics(),
        }), 500
    except FormLoadError as e:
        logger.exception(f"Google Form load/parse failed: {e}")
        return jsonify({"error": "The Google Form could not be loaded or parsed."}), 500
    except FormExtractionError as e:
        logger.exception(f"Unknown form extraction failure: {e}")
        return jsonify({"error": "The form could not be extracted because of an unexpected extraction error."}), 500
    except Exception as e:
        logger.exception(f"Unexpected source form extraction failure: {e}")
        return jsonify({"error": "The form could not be extracted because of an unknown error."}), 500

    return jsonify({
        "success": True,
        "form": {
            "id": form.id,
            "title": form.title,
            "description": form.description,
            "url": str(form.url),
        },
    })


@bp.route('/form_copy/preview_plan', methods=['POST'])
def form_copy_preview_plan():
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)

    if not form:
        return jsonify({"error": "Form not found"}), 404

    plan = FormCopyPlanner().build_plan(form)
    return jsonify({"success": True, "plan": plan.model_dump(mode="json")})


@bp.route('/form_copy/apply_to_target', methods=['POST'])
def form_copy_apply_to_target():
    data = request.get_json(silent=True) or {}
    form_id = data.get('form_id')
    target_url = data.get('target_url')
    ownership_confirmed = data.get('ownership_confirmed') is True

    if not form_id:
        return jsonify({"error": "No form_id provided"}), 400
    if not target_url:
        return jsonify({"error": "No target edit URL provided"}), 400
    if not is_google_form_edit_url(target_url):
        return jsonify({"error": "Please enter a valid Google Forms edit URL."}), 400
    if not ownership_confirmed:
        return jsonify({"error": "Please confirm you own or control the target form before applying changes."}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_id(form_id)

    if not form:
        return jsonify({"error": "Form not found"}), 404

    plan = FormCopyPlanner().build_plan(form)
    copier = FormCopier(
        chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
        chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
        headless=True,
    )
    result = copier.apply_plan(plan, target_url)
    status_code = 200 if result.status in ("success", "partial") else 500
    return jsonify({"success": result.status in ("success", "partial"), "result": result.model_dump(mode="json")}), status_code


@bp.route('/form_filling/extract', methods=['POST'])
def extract():
    """
    Extract Form Data

    POST /extract
    - Extracts form structure from a Google Form URL
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
        
    form_url = data.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400
    if not isinstance(form_url, str):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
    form_url = form_url.strip()
    if not _is_valid_google_forms_url(form_url):
        return jsonify({"error": "Please enter a valid Google Form URL."}), 400
        
    session['form_url'] = form_url

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)
        if not form:
            form_extractor = FormExtractor(
                chromebinary_path=get_chrome_binary(Config.CHROME_BINARY_PATH),
                chromedriver_path=get_chromedriver_path(Config.CHROME_DRIVER_PATH),
                headless=True
            )
            try:
                form = form_extractor.extract_form_data(form_url)
                storage.save_form(form)
            except ValueError as e:
                logger.warning(f"Invalid Google Form URL: {form_url}. Details: {str(e)}")
                return jsonify({"error": "Please enter a valid Google Form URL."}), 400
            except DriverStartupError as e:
                logger.exception(f"Chrome/ChromeDriver startup failed while extracting form: {e}")
                return jsonify({
                    "error": (
                        "Chrome or ChromeDriver could not start. Please check that Chrome is installed, "
                        "ChromeDriver is available, and the runtime diagnostics paths are writable."
                    ),
                    "diagnostics": _runtime_diagnostics(),
                }), 500
            except FormLoadError as e:
                logger.exception(f"Google Form load/parse failed: {e}")
                return jsonify({
                    "error": (
                        "The Google Form could not be loaded or parsed. Please check that the form URL "
                        "opens in a browser and the form is accessible."
                    )
                }), 500
            except FormExtractionError as e:
                logger.exception(f"Unknown form extraction failure: {e}")
                return jsonify({
                    "error": "The form could not be extracted because of an unexpected extraction error."
                }), 500
            except Exception as e:
                logger.exception(f"Unexpected form extraction failure: {e}")
                return jsonify({
                    "error": "The form could not be extracted because of an unknown error."
                }), 500
    return jsonify({"success": True, "message": "Form extracted successfully"})


@bp.route('/form_filling/preview', methods=['GET'])
def preview():
    """
    Preview Extracted Form

    GET /form_filling/preview
    - Returns the extracted form data stored in session
    """
    form_url = session.get('form_url')
    if not form_url:
        return jsonify({"error": "No form URL provided"}), 400

    with get_storage_service() as storage:
        form = storage.get_form_by_url(form_url)

    if not form:
        return jsonify({"error": "No data found for this form"}), 404

    return jsonify(form.model_dump(mode='json'))
