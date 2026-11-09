from urllib.parse import urlparse

from app.models import CopyPlan, CopyResult, CopyWarning


def is_google_form_edit_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    parts = parsed.path.strip("/").split("/")
    return (
        parsed.scheme == "https"
        and parsed.netloc == "docs.google.com"
        and len(parts) >= 4
        and parts[0] == "forms"
        and parts[1] == "d"
        and parts[3] == "edit"
    )


class FormCopier:
    def __init__(self, chromebinary_path=None, chromedriver_path=None, headless=True, driver_factory=None):
        self.chromebinary_path = chromebinary_path
        self.chromedriver_path = chromedriver_path
        self.headless = headless
        self.driver_factory = driver_factory

    def apply_plan(self, plan: CopyPlan, target_url: str) -> CopyResult:
        if not is_google_form_edit_url(target_url):
            return CopyResult(
                status="failure",
                operations_total=len(plan.operations),
                warnings=[CopyWarning(code="invalid_target_url", message="Target must be a Google Forms edit URL.")],
            )

        driver = None
        operation_results = []
        warnings = list(plan.warnings)
        succeeded = 0
        failed = 0
        skipped = 0

        try:
            driver = self._create_driver()
            driver.get(target_url)
            if not self._is_editable_form(driver):
                return CopyResult(
                    status="failure",
                    operations_total=len(plan.operations),
                    warnings=warnings + [CopyWarning(code="target_not_editable", message="Target form editor could not be validated.")],
                    operation_results=operation_results,
                )

            for operation in plan.operations:
                if operation.capability != "supported":
                    skipped += 1
                    warning = CopyWarning(
                        code="operation_skipped",
                        message=f"Question type '{operation.question_type}' is {operation.capability} and was skipped.",
                        question_id=operation.source_question_id,
                        question_text=operation.source_question_text,
                        capability=operation.capability,
                    )
                    warnings.append(warning)
                    operation_results.append({"operation_id": operation.operation_id, "kind": operation.kind, "status": "skipped"})
                    continue

                try:
                    self._apply_operation(driver, operation)
                    operation_results.append({"operation_id": operation.operation_id, "kind": operation.kind, "status": "success"})
                    succeeded += 1
                except NotImplementedError as exc:
                    skipped += 1
                    warning = CopyWarning(
                        code="operation_not_implemented",
                        message=str(exc),
                        question_id=operation.source_question_id,
                        question_text=operation.source_question_text,
                        capability=operation.capability,
                    )
                    warnings.append(warning)
                    operation_results.append({"operation_id": operation.operation_id, "kind": operation.kind, "status": "skipped", "error": str(exc)})
                except Exception as exc:
                    failed += 1
                    warning = CopyWarning(
                        code="operation_failed",
                        message=str(exc),
                        question_id=operation.source_question_id,
                        question_text=operation.source_question_text,
                        capability=operation.capability,
                    )
                    warnings.append(warning)
                    operation_results.append({"operation_id": operation.operation_id, "kind": operation.kind, "status": "failure", "error": str(exc)})

            status = "success" if failed == 0 and skipped == 0 else "partial"
            return CopyResult(
                status=status,
                operations_total=len(plan.operations),
                operations_succeeded=succeeded,
                operations_failed=failed,
                warnings=warnings,
                operation_results=operation_results,
            )
        except Exception as exc:
            return CopyResult(
                status="failure",
                operations_total=len(plan.operations),
                operations_succeeded=succeeded,
                operations_failed=failed or len(plan.operations),
                warnings=warnings + [CopyWarning(code="copy_failed", message=str(exc))],
                operation_results=operation_results,
            )
        finally:
            if driver is not None:
                driver.quit()

    def _create_driver(self):
        if self.driver_factory:
            return self.driver_factory()
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        if self.chromebinary_path:
            options.binary_location = self.chromebinary_path
        service = Service(self.chromedriver_path) if self.chromedriver_path else None
        return webdriver.Chrome(service=service, options=options)

    def _is_editable_form(self, driver) -> bool:
        return "docs.google.com/forms" in getattr(driver, "current_url", "")

    def _apply_operation(self, driver, operation):
        if operation.kind == "set_title_description":
            self._set_title_description(driver, operation.payload.get("title", ""), operation.payload.get("description", ""))
            return
        if operation.kind == "create_question":
            self._create_question(driver, operation)
            return
        raise ValueError(f"Unsupported copy operation: {operation.kind}")

    def _set_title_description(self, driver, title: str, description: str):
        self._record_action(driver, "set_title", title)
        self._record_action(driver, "set_description", description)

    def _create_question(self, driver, operation):
        question_type = operation.question_type
        if question_type not in {"short_answer", "paragraph", "multiple_choice", "checkbox", "dropdown"}:
            raise ValueError(f"Question type '{question_type}' is not supported for copy.")
        self._record_action(driver, "create_question", {
            "type": question_type,
            "text": operation.payload.get("text", ""),
            "options": operation.payload.get("options", []),
        })

    def _record_action(self, driver, action: str, payload):
        if hasattr(driver, "record_action"):
            driver.record_action(action, payload)
            return
        raise NotImplementedError("Google Forms editor mutation is not implemented for live Selenium drivers yet.")