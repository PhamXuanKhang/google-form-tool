"""
Form Submitter Module

This module handles the automated submission of Google Forms using Selenium.
It supports multi-threaded submissions, rate limiting, and status monitoring.
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException,
)

from app.models import Form, Question, Submission
from app.core.form_processor import FormProcessor
from app.core.prefill_link_generator import PrefillLinkGenerator
from app.logging_config import logger

SUBMISSION_MODE_PREFILL = "prefill_link"
SUBMISSION_MODE_DOM_FILL = "dom_fill"
VALID_SUBMISSION_MODES = (SUBMISSION_MODE_PREFILL, SUBMISSION_MODE_DOM_FILL)
SKIPPABLE_PREFILL_TYPES = {"file_upload", "rating", "unknown"}
PREFILL_MAX_BUTTON_CLICKS = 25
REQUIRED_ERROR_MARKERS = (
    "this is a required question",
    "required question",
    "đây là một câu hỏi bắt buộc",
    "câu hỏi này là bắt buộc",
)
REQUIRED_LEGEND_MARKERS = (
    "biểu thị câu hỏi bắt buộc",
    "indicates required question",
)

import threading
import time
import random
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from datetime import datetime
from functools import wraps
from typing import Dict, List, Any, Optional, Callable

HIGH_FAILURE_WARNING_THRESHOLD = 80
HIGH_FAILURE_WARNING_MESSAGE = (
    "Many submissions failed. Check required answers, form changes, or extract the form again."
)


def retry_on_stale(max_retries: int = 3, delay: float = 0.5):
    """Decorator that retries function on StaleElementReferenceException."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Stale element, retry {attempt + 1}/{max_retries}")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class FormSubmitter:
    """
    Automates the submission of Google Forms with configurable options for
    concurrent submissions, retry logic, and submission monitoring.
    """
    
    def __init__(self, 
                 form: Form, 
                 chromebinary_path: str = None, 
                 chromedriver_path: str = None,
                 headless: bool = True):
        """
        Initialize the FormSubmitter with form data and browser configuration.
        
        Args:
            form (Form): The form to submit
            chromebinary_path (str): Path to Chrome binary
            chromedriver_path (str): Path to ChromeDriver
            headless (bool): Whether to run the browser in headless mode
        """
        self.form = form
        self.chromebinary_path = chromebinary_path
        self.chromedriver_path = chromedriver_path
        self.headless = headless
        
        self.status_lock = threading.RLock()
        self.status = self._new_status()
        
        self.stop_flag = threading.Event()
        self.threads = []

        # Prefill-mode queue (populated by submit_form or submit_prefilled_urls).
        self.urls_queue: Optional[List[str]] = None
        self.urls_lock: Optional[threading.Lock] = None
        
        self.form_processor = FormProcessor(self.form)
        
        self.option_arguments = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-notifications',
            '--log-level=3'
        ]

        self._question_type_lookup = self._build_question_type_lookup()
        self.skipped_prefill_summary: Dict[str, int] = {}
        
        if self.headless:
            self.option_arguments.append('--headless')
    
    def initialize_driver(self):
        """
        Initialize and configure a new Chrome WebDriver instance.
        
        Returns:
            webdriver.Chrome: Configured WebDriver instance
        """
        options = Options()
        for arg in self.option_arguments:
            options.add_argument(arg)
        
        if self.chromebinary_path:
            options.binary_location = self.chromebinary_path
        
        try:
            service = (
                Service(executable_path=self.chromedriver_path)
                if self.chromedriver_path
                else Service()  # Selenium Manager auto-downloads the correct driver
            )
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    @staticmethod
    def _new_status() -> Dict[str, Any]:
        return {
            "running": False,
            "total": 0,
            "success": 0,
            "failed": 0,
            "current_threads": 0,
            "start_time": None,
            "end_time": None,
            "success_rate": 0,
            "warning": None,
        }

    def _increment_status(self, key: str, amount: int = 1) -> None:
        with self.status_lock:
            self.status[key] += amount

    def _set_status_values(self, **values: Any) -> None:
        with self.status_lock:
            self.status.update(values)

    def _status_snapshot(self) -> Dict[str, Any]:
        with self.status_lock:
            return dict(self.status)

    def submit_form(self,
                    num_submissions: int = 1,
                    concurrent_threads: int = 1,
                    min_delay: int = 1,
                    max_delay: int = 5,
                    responses: Optional[Dict[str, Any]] = None,
                    responses_list: Optional[List[Dict[str, Any]]] = None,
                    submission_mode: str = SUBMISSION_MODE_PREFILL,
                    callback: Optional[Callable] = None) -> Submission:
        """
        Start the form submission process with specified parameters.

        Args:
            num_submissions (int): Number of submissions to make
            concurrent_threads (int): Number of concurrent submission threads
            min_delay (int): Minimum delay between submissions (seconds)
            max_delay (int): Maximum delay between submissions (seconds)
            responses (Dict[str, Any], optional): Single response dict for all submissions
            responses_list (List[Dict[str, Any]], optional): List of responses, one per submission
            callback (Callable, optional): Function to call after each submission

        Returns:
            Submission: Submission record with results
        """
        if submission_mode not in VALID_SUBMISSION_MODES:
            raise ValueError(
                f"Unknown submission_mode '{submission_mode}'. "
                f"Expected one of: {VALID_SUBMISSION_MODES}"
            )
        if num_submissions <= 0:
            raise ValueError("num_submissions must be greater than 0")
        if concurrent_threads <= 0:
            raise ValueError("concurrent_threads must be greater than 0")

        self.submission_mode = submission_mode

        # Data-driven mode: each item in responses_list is one submission
        if responses_list:
            num_submissions = len(responses_list)
            self.responses_queue = list(responses_list)
            self.responses_lock = threading.Lock()
            self.data_driven_mode = True
        else:
            self.responses_queue = None
            self.data_driven_mode = False

        # Prefill mode: generate URLs up-front and let workers pop from queue.
        # If a caller (e.g. submit_prefilled_urls) has pre-populated
        # self.urls_queue, respect it and skip the generator entirely.
        if submission_mode == SUBMISSION_MODE_PREFILL:
            if not self.urls_queue:
                response_dicts = self._build_response_dicts(
                    num_submissions, responses, responses_list
                )
                response_dicts, skipped_summary = self._filter_skippable_responses(
                    response_dicts
                )
                self.skipped_prefill_summary = skipped_summary
                num_submissions = len(response_dicts)
                generator = PrefillLinkGenerator(self.form)
                self.urls_queue = generator.build_prefill_urls(response_dicts)
                self.urls_lock = threading.Lock()
            else:
                num_submissions = len(self.urls_queue)
                if self.urls_lock is None:
                    self.urls_lock = threading.Lock()
            logger.info(
                f"Prepared {len(self.urls_queue)} prefill URLs for submission"
            )
            if self.skipped_prefill_summary:
                logger.warning(
                    "Skipping unsupported prefill types: %s",
                    self.skipped_prefill_summary,
                )
        else:
            self.urls_queue = None
            self.urls_lock = None

        # Reset status
        with self.status_lock:
            self.status = self._new_status()
            self.status.update({
                "running": True,
                "total": num_submissions,
                "start_time": datetime.now(),
            })
        self.skipped_prefill_summary = {}

        self.stop_flag.clear()

        # Generate responses if not provided (for non-data-driven dom-fill mode)
        if submission_mode == SUBMISSION_MODE_DOM_FILL and not self.data_driven_mode:
            self.responses = responses or self.form_processor.generate_random_responses()

        worker_target = (
            self._prefill_worker
            if submission_mode == SUBMISSION_MODE_PREFILL
            else self._submission_worker
        )

        effective_threads = min(concurrent_threads, num_submissions)
        base_submissions = num_submissions // effective_threads
        remainder = num_submissions % effective_threads

        try:
            # Start submission threads
            for i in range(effective_threads):
                submissions_per_thread = base_submissions + (1 if i < remainder else 0)

                thread = threading.Thread(
                    target=worker_target,
                    args=(submissions_per_thread, min_delay, max_delay, callback)
                )
                self.threads.append(thread)
                thread.start()
                self._increment_status("current_threads")

            # Wait for all threads to complete
            for thread in self.threads:
                thread.join()
        finally:
            with self.status_lock:
                self.status["running"] = False
                self.status["end_time"] = datetime.now()
                if self.status["total"] > 0:
                    self.status["success_rate"] = (self.status["success"] / self.status["total"]) * 100
                if self.status["success_rate"] < HIGH_FAILURE_WARNING_THRESHOLD:
                    self.status["warning"] = HIGH_FAILURE_WARNING_MESSAGE
                else:
                    self.status["warning"] = None
                final_status = dict(self.status)

        if final_status["warning"]:
            logger.warning(
                f"{HIGH_FAILURE_WARNING_MESSAGE} Success rate: {final_status['success_rate']:.2f}% "
                f"({final_status['success']}/{final_status['total']})"
            )

        time_used = 0
        if final_status["start_time"] and final_status["end_time"]:
            time_used = int((final_status["end_time"] - final_status["start_time"]).total_seconds())
        
        submission = Submission(
            num_submission=final_status["total"],
            concurrent_thread=concurrent_threads,
            time_used=time_used,
            success_rate=final_status["success_rate"],
            network_status="Completed"
        )
        
        logger.info(f"Form submission completed: {submission.submission_id}")
        logger.info(f"Success rate: {submission.success_rate:.2f}% ({final_status['success']}/{final_status['total']})")
        
        return submission
    
    def _submission_worker(self,
                          num_submissions: int,
                          min_delay: int,
                          max_delay: int,
                          callback: Optional[Callable] = None) -> None:
        """
        Worker thread function for submitting forms.

        Args:
            num_submissions (int): Number of submissions for this thread
            min_delay (int): Minimum delay between submissions (seconds)
            max_delay (int): Maximum delay between submissions (seconds)
            callback (Callable, optional): Function to call after each submission
        """
        driver = None

        try:
            driver = self.initialize_driver()

            for _ in range(num_submissions):
                if self.stop_flag.is_set():
                    logger.info("Submission worker stopped early due to stop flag")
                    break

                # In data-driven mode, get next response from queue
                if self.data_driven_mode:
                    with self.responses_lock:
                        if not self.responses_queue:
                            logger.info("No more responses in queue")
                            break
                        self.responses = self.responses_queue.pop(0)

                success = self._submit_single_form(driver)

                if success:
                    self._increment_status("success")
                else:
                    self._increment_status("failed")

                if callback:
                    callback(success)

                # Random delay between submissions
                if _ < num_submissions - 1 and not self.stop_flag.is_set():
                    delay = random.uniform(min_delay, max_delay)
                    time.sleep(delay)
        
        except Exception as e:
            logger.error(f"Error in submission worker: {str(e)}")
        
        finally:
            self._increment_status("current_threads", -1)
            if driver:
                driver.quit()
    
    def _build_response_dicts(
        self,
        num_submissions: int,
        responses: Optional[Dict[str, Any]],
        responses_list: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Materialize the response dictionaries used to build prefill URLs.

        - Data-driven: use ``responses_list`` directly.
        - Single response (e.g. AI mode): replicate ``responses`` N times.
        - Manual/random: generate N random responses using FormProcessor.
        """
        if responses_list:
            return self.form_processor.apply_prefill_branch_stops(
                [dict(response) for response in responses_list]
            )
        if responses is not None:
            return self.form_processor.apply_prefill_branch_stops(
                [dict(responses) for _ in range(num_submissions)]
            )
        return self.form_processor.generate_prefill_responses(num_submissions)

    def prepare_prefill_queue(
        self,
        num_submissions: int,
        responses: Optional[Dict[str, Any]],
        responses_list: Optional[List[Dict[str, Any]]],
        include_debug_sample: bool = False,
    ) -> tuple[int, Dict[str, int], Optional[str]]:
        response_dicts = self._build_response_dicts(
            num_submissions, responses, responses_list
        )
        response_dicts, skipped_summary = self._filter_skippable_responses(
            response_dicts
        )
        generator = PrefillLinkGenerator(self.form)
        self.urls_queue = generator.build_prefill_urls(response_dicts)
        self.urls_lock = threading.Lock()
        self.skipped_prefill_summary = skipped_summary

        debug_sample = None
        if include_debug_sample and self.urls_queue:
            debug_sample = self._format_prefill_url_for_log(self.urls_queue[0])

        return len(self.urls_queue), skipped_summary, debug_sample

    def _prefill_worker(self,
                        num_submissions: int,
                        min_delay: int,
                        max_delay: int,
                        callback: Optional[Callable] = None) -> None:
        """Worker thread: open prefill URLs from the shared queue and submit."""
        driver = None
        try:
            driver = self.initialize_driver()

            for iteration in range(num_submissions):
                if self.stop_flag.is_set():
                    logger.info("Prefill worker stopped early due to stop flag")
                    break

                with self.urls_lock:
                    if not self.urls_queue:
                        logger.info("No more prefill URLs in queue")
                        break
                    url = self.urls_queue.pop(0)

                success = self._submit_prefilled_url(driver, url)

                if success:
                    self._increment_status("success")
                else:
                    self._increment_status("failed")

                if callback:
                    callback(success)

                if iteration < num_submissions - 1 and not self.stop_flag.is_set():
                    time.sleep(random.uniform(min_delay, max_delay))

        except Exception as e:
            logger.error(f"Error in prefill worker: {str(e)}")

        finally:
            self._increment_status("current_threads", -1)
            if driver:
                driver.quit()

    def submit_prefilled_urls(
        self,
        urls: List[str],
        concurrent_threads: int = 1,
        min_delay: int = 1,
        max_delay: int = 5,
        callback: Optional[Callable] = None,
    ) -> Submission:
        """Public helper: submit a prepared list of prefill URLs.

        Useful when callers (e.g. tests, scripts) already have prefill URLs
        and don't need the full ``submit_form`` orchestration.
        """
        self.urls_queue = list(urls)
        self.urls_lock = threading.Lock()
        return self.submit_form(
            num_submissions=len(urls),
            concurrent_threads=concurrent_threads,
            min_delay=min_delay,
            max_delay=max_delay,
            responses_list=None,
            responses=None,
            submission_mode=SUBMISSION_MODE_PREFILL,
            callback=callback,
        )

    def _build_question_type_lookup(self) -> Dict[str, str]:
        lookup = {}
        if not self.form.response_config or not self.form.response_config.pages:
            return lookup
        for page in self.form.response_config.pages:
            for question in page.questions or []:
                if question.question_id:
                    lookup[question.question_id] = question.type
                entry_param = question.get_entry_param()
                if entry_param:
                    lookup[entry_param] = question.type
        return lookup

    def _filter_skippable_responses(
        self,
        responses_list: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        skipped_summary: Dict[str, int] = {}
        filtered = []
        for responses in responses_list:
            cleaned = {}
            for key, value in responses.items():
                q_type = self._question_type_lookup.get(key)
                if q_type in SKIPPABLE_PREFILL_TYPES:
                    skipped_summary[q_type] = skipped_summary.get(q_type, 0) + 1
                    continue
                cleaned[key] = value
            filtered.append(cleaned)
        return filtered, skipped_summary

    @staticmethod
    def _format_prefill_url_for_log(url: str) -> str:
        sensitive_params = {"emailAddress"}
        try:
            parts = urlsplit(url)
            redacted_query = urlencode(
                [
                    (key, "[REDACTED]" if key.startswith("entry.") or key in sensitive_params else value)
                    for key, value in parse_qsl(parts.query, keep_blank_values=True)
                ],
                doseq=True,
            )
            return urlunsplit((parts.scheme, parts.netloc, parts.path, redacted_query, parts.fragment))
        except Exception:
            return "[REDACTED_PREFILL_URL]"

    def _submit_prefilled_url(self, driver, url: str) -> bool:
        """Open a prefill URL and click through Next/Submit pages."""
        try:
            driver.get(url)
            start_url = driver.current_url
            button_clicks = 0

            while True:
                if button_clicks >= PREFILL_MAX_BUTTON_CLICKS:
                    diagnostics = self._collect_prefill_submit_diagnostics(driver)
                    logger.warning(
                        "Prefill submit stopped after too many page actions for %s%s",
                        self._format_prefill_url_for_log(start_url),
                        f" ({diagnostics})" if diagnostics else "",
                    )
                    return False

                try:
                    self._fill_unanswered_choice_controls(driver)
                    next_button = WebDriverWait(driver, 8).until(
                        lambda d: self._find_form_button(d, ("next", "tiep"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    driver.execute_script("arguments[0].click();", next_button)
                    button_clicks += 1
                    time.sleep(1.5)
                    diagnostics = self._collect_prefill_submit_diagnostics(driver)
                    if diagnostics:
                        logger.warning(
                            "Prefill validation failed after Next for %s: %s",
                            self._format_prefill_url_for_log(start_url),
                            diagnostics,
                        )
                        return False

                except TimeoutException:
                    # No Next button found — look for Submit
                    try:
                        self._fill_unanswered_choice_controls(driver)
                        submit_button = WebDriverWait(driver, 8).until(
                            lambda d: self._find_form_button(
                                d,
                                ("submit", "gui"),
                                fallback_initials=("g",),
                            )
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                        driver.execute_script("arguments[0].click();", submit_button)
                        button_clicks += 1

                        result = WebDriverWait(driver, 10).until(
                            lambda d: self._prefill_submit_result(d, submit_button, start_url)
                        )
                        if result == "validation_error":
                            diagnostics = self._collect_prefill_submit_diagnostics(driver)
                            logger.warning(
                                "Prefill validation failed after Submit for %s: %s",
                                self._format_prefill_url_for_log(start_url),
                                diagnostics or "unknown validation error",
                            )
                            return False
                        logger.info("Prefill URL submitted successfully")
                        return True

                    except (TimeoutException, NoSuchElementException) as e:
                        diagnostics = self._collect_prefill_submit_diagnostics(driver)
                        logger.warning(
                            "Prefill submit confirmation failed for %s: %s%s",
                            self._format_prefill_url_for_log(start_url),
                            type(e).__name__,
                            f" ({diagnostics})" if diagnostics else "",
                        )
                        return False

        except Exception as e:
            logger.error(
                "Error submitting prefill URL %s: %s",
                self._format_prefill_url_for_log(url),
                type(e).__name__,
            )
            return False

    def _find_form_button(
        self,
        driver,
        labels: tuple[str, ...],
        fallback_initials: tuple[str, ...] = (),
    ):
        buttons = driver.find_elements(By.XPATH, "//div[@role='button']")
        for button in buttons:
            try:
                if hasattr(button, "is_displayed") and not button.is_displayed():
                    continue
                if hasattr(button, "is_enabled") and not button.is_enabled():
                    continue
                text = self._normalize_button_text(button.text)
                if text and any(label in text for label in labels):
                    return button
            except StaleElementReferenceException:
                continue

        for button in buttons:
            try:
                if hasattr(button, "is_displayed") and not button.is_displayed():
                    continue
                if hasattr(button, "is_enabled") and not button.is_enabled():
                    continue
                text = self._normalize_button_text(button.text)
                if text and any(text == initial or text.startswith(initial) for initial in fallback_initials):
                    logger.info("Matched form button by fallback text: %s", button.text)
                    return button
            except StaleElementReferenceException:
                continue

        return False

    @staticmethod
    def _normalize_button_text(text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text or "")
        without_marks = "".join(
            char for char in decomposed
            if unicodedata.category(char) != "Mn"
        )
        return " ".join(without_marks.lower().split())

    def _prefill_submit_result(self, driver, submit_button, start_url: str):
        if self._collect_prefill_submit_diagnostics(driver):
            return "validation_error"
        if EC.staleness_of(submit_button)(driver):
            return "submitted"
        if driver.current_url != start_url:
            return "submitted"
        if driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'response') or "
            "contains(text(), 'submitted') or "
            "contains(text(), 'recorded') or "
            "contains(text(), 'gửi') or "
            "contains(text(), 'ghi lại') or "
            "contains(text(), 'đã được ghi') or "
            "contains(text(), 'Câu trả lời')]"
        ):
            return "submitted"
        return False

    def _fill_unanswered_choice_controls(self, driver) -> None:
        """Select a first option only for visible choice groups with no selection.

        Prefill links cannot cover every Google Forms control type. This keeps
        existing prefilled answers intact and only supplies a fallback for
        unanswered visible radio/checkbox groups that would block navigation or
        final submit when required.
        """
        try:
            radio_groups = driver.find_elements(By.XPATH, "//div[@role='radiogroup']")
            filled_radios = 0
            for group in radio_groups:
                try:
                    checked = group.find_elements(By.XPATH, ".//div[@role='radio' and @aria-checked='true']")
                    if checked:
                        continue
                    radios = group.find_elements(By.XPATH, ".//div[@role='radio']")
                    if radios:
                        driver.execute_script("arguments[0].click();", radios[0])
                        filled_radios += 1
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            checkbox_containers = driver.find_elements(
                By.XPATH,
                "//div[@data-params and .//div[@role='checkbox']]"
            )
            filled_checkboxes = 0
            for container in checkbox_containers:
                try:
                    checked = container.find_elements(By.XPATH, ".//div[@role='checkbox' and @aria-checked='true']")
                    if checked:
                        continue
                    checkbox = container.find_element(By.XPATH, ".//div[@role='checkbox']")
                    driver.execute_script("arguments[0].click();", checkbox)
                    filled_checkboxes += 1
                except (NoSuchElementException, StaleElementReferenceException):
                    continue

            if filled_radios or filled_checkboxes:
                logger.info(
                    "Filled unanswered visible choice controls before submit: radios=%s checkboxes=%s",
                    filled_radios,
                    filled_checkboxes,
                )
        except Exception as e:
            logger.debug("Could not fill unanswered choice controls: %s", type(e).__name__)

    def _collect_prefill_submit_diagnostics(self, driver) -> str:
        try:
            diagnostics = []
            question_containers = driver.find_elements(By.XPATH, "//div[@data-params]")
            for container in question_containers:
                text = (container.text or "").strip()
                diagnostic = self._extract_required_error_diagnostic(text)
                if diagnostic and diagnostic not in diagnostics:
                    diagnostics.append(diagnostic)
                if len(diagnostics) >= 5:
                    return "; ".join(diagnostics)

            error_elements = driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'required') or "
                "contains(text(), 'Required') or "
                "contains(text(), 'bắt buộc') or "
                "contains(text(), 'Bắt buộc')]"
            )
            for element in error_elements[:5]:
                text = (element.text or "").strip()
                if self._is_required_error_text(text) and text not in diagnostics:
                    diagnostics.append(text)
            return "; ".join(diagnostics)
        except Exception:
            return ""

    @staticmethod
    def _is_required_error_text(text: str) -> bool:
        normalized = " ".join((text or "").split()).lower()
        if not normalized:
            return False
        if any(marker in normalized for marker in REQUIRED_LEGEND_MARKERS):
            return False
        return any(marker in normalized for marker in REQUIRED_ERROR_MARKERS)

    def _extract_required_error_diagnostic(self, text: str) -> str:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        if not lines:
            return ""

        error_line = next((line for line in lines if self._is_required_error_text(line)), "")
        if not error_line:
            return ""

        title = ""
        for line in lines:
            if line == error_line or self._is_required_error_text(line):
                continue
            if line in ("*",):
                continue
            title = line
            break

        return f"{title}: {error_line}" if title else error_line

    def _submit_single_form(self, driver) -> bool:
        """
        Submit a single form instance with the current response data.
        
        Args:
            driver (webdriver.Chrome): WebDriver instance to use
            
        Returns:
            bool: True if submission was successful, False otherwise
        """
        try:
            # Load the form URL
            driver.get(str(self.form.url))
            
            # Wait for form to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            current_page = 1
            
            while True:
                # Fill in the current page
                if not self._fill_page(driver, current_page):
                    logger.warning(f"Failed to fill page {current_page}")
                    return False
                
                # Try to find and click Next or Submit button
                try:
                    next_button = self._find_form_button(driver, ("next", "tiep"))
                    if not next_button:
                        raise NoSuchElementException("Next button not found")
                    driver.execute_script("arguments[0].click();", next_button)
                    current_page += 1
                    time.sleep(1)

                except NoSuchElementException:
                    # If no Next button, look for Submit button
                    try:
                        submit_button = self._find_form_button(
                            driver, ("submit", "gui"), fallback_initials=("g",)
                        )
                        if not submit_button:
                            raise NoSuchElementException("Submit button not found")
                        driver.execute_script("arguments[0].click();", submit_button)

                        # Wait for submission confirmation
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'response') or contains(text(), 'submitted') or contains(text(), 'gửi')]"))
                        )

                        logger.info("Form submitted successfully")
                        return True

                    except (NoSuchElementException, TimeoutException):
                        logger.error("Could not find Submit button or submission failed")
                        return False
        
        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            return False
    
    def _fill_page(self, driver, page_num: int) -> bool:
        """
        Fill all questions on the current page of the form.
        
        Args:
            driver (webdriver.Chrome): WebDriver instance to use
            page_num (int): Current page number (1-based)
            
        Returns:
            bool: True if all fields were filled successfully, False otherwise
        """
        if not self.form.response_config or not self.form.response_config.pages:
            logger.error("Form has no response configuration")
            return False
        
        # Get the current page (adjust for 0-based indexing)
        if page_num > len(self.form.response_config.pages):
            logger.error(f"Page {page_num} does not exist in form configuration")
            return False
        
        page = self.form.response_config.pages[page_num - 1]
        
        if not page.questions:
            logger.warning(f"Page {page_num} has no questions")
            return True  # Not necessarily an error
        
        # Fill each question on the page
        for question in page.questions:
            try:
                self._fill_question(driver, question)
            except Exception as e:
                logger.error(f"Error filling question {question.question_id}: {str(e)}")
                # Continue with other questions even if one fails
        
        return True
    
    @retry_on_stale(max_retries=3, delay=0.3)
    def _fill_question(self, driver, question: Question) -> None:
        """
        Fill a single question based on its type and the response data.

        Args:
            driver (webdriver.Chrome): WebDriver instance to use
            question (Question): The question to fill
        """
        # Skip if no response for this question
        if question.question_id not in self.responses:
            return
        
        response = self.responses[question.question_id]
        
        try:
            # Find question container
            # Regular questions have data-params with question_id
            # Email field is special case
            if question.question_id == "q_email":
                self._fill_email_field(driver, response)
            else:
                question_container = driver.find_element(
                    By.XPATH, f"//div[contains(@data-params, '{question.question_id}')]"
                )
                
                # Fill based on question type
                if question.type == "input_email":
                    self._fill_email_field(driver, response)
                    
                elif question.type in ["input_text", "time"]:
                    text_fields = question_container.find_elements(By.XPATH, ".//input[@type='text']")
                    for field in text_fields:
                        field.clear()
                        field.send_keys(str(response))
                
                elif question.type == "textarea":
                    textarea = question_container.find_element(By.XPATH, ".//textarea")
                    textarea.clear()
                    textarea.send_keys(str(response))
                
                elif question.type == "date":
                    date_field = question_container.find_element(By.XPATH, ".//input[@type='date']")
                    date_field.clear()
                    date_field.send_keys(str(response))
                
                elif question.type == "dropdown":
                    dropdown = question_container.find_element(By.XPATH, ".//div[@role='listbox']")
                    driver.execute_script("arguments[0].click();", dropdown)
                    time.sleep(0.5)

                    options = driver.find_elements(By.XPATH, "//div[@role='option']")
                    target = self._normalize_button_text(str(response))
                    matched = [o for o in options if self._normalize_button_text(o.text) == target]
                    if not matched:
                        matched = options
                    if matched:
                        driver.execute_script("arguments[0].click();", matched[0])
                
                elif question.type == "multiple_choice":
                    # Find radio option matching our response
                    radio_options = question_container.find_elements(
                        By.XPATH, f".//div[@role='radio']/parent::div/parent::div"
                    )
                    
                    for option in radio_options:
                        option_text = option.text.strip()
                        if option_text == response:
                            radio = option.find_element(By.XPATH, ".//div[@role='radio']")
                            driver.execute_script("arguments[0].click();", radio)
                            break
                    else:
                        # If no match, select first option
                        first_radio = question_container.find_element(By.XPATH, ".//div[@role='radio']")
                        driver.execute_script("arguments[0].click();", first_radio)
                
                elif question.type == "checkbox":
                    # Multiple selections possible
                    if not isinstance(response, list):
                        response = [response]
                    
                    checkboxes = question_container.find_elements(
                        By.XPATH, f".//div[@role='checkbox']/parent::div/parent::div"
                    )
                    
                    for checkbox in checkboxes:
                        option_text = checkbox.text.strip()
                        if option_text in response:
                            checkbox_element = checkbox.find_element(By.XPATH, ".//div[@role='checkbox']")
                            driver.execute_script("arguments[0].click();", checkbox_element)
                
                elif question.type == "linear_scale":
                    # Find the radio button corresponding to the scale value
                    scale_options = question_container.find_elements(By.XPATH, ".//div[@role='radio']")
                    if 0 <= response - 1 < len(scale_options):
                        driver.execute_script("arguments[0].click();", scale_options[response - 1])
                    else:
                        # Default to first option
                        driver.execute_script("arguments[0].click();", scale_options[0])
                
                elif question.type == "rank":
                    # Complex type - implementation depends on exact form structure
                    pass  # Placeholder - actual implementation would require form-specific logic
        
        except (NoSuchElementException, ElementNotInteractableException) as e:
            logger.warning(f"Could not fill question {question.question_id}: {str(e)}")
    
    def _fill_email_field(self, driver, email: str) -> None:
        """
        Special handler for email fields which can appear in different contexts.
        
        Args:
            driver (webdriver.Chrome): WebDriver instance to use
            email (str): Email address to fill
        """
        try:
            email_fields = driver.find_elements(By.XPATH, "//input[@type='email']")
            for field in email_fields:
                field.clear()
                field.send_keys(email)
        except (NoSuchElementException, ElementNotInteractableException) as e:
            logger.warning(f"Could not fill email field: {str(e)}")
    
    def stop(self) -> None:
        """
        Stop all ongoing submission threads.
        """
        self.stop_flag.set()
        logger.info("Stopping form submission threads")
        
        # Wait for all threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self._set_status_values(running=False, end_time=datetime.now())
        
        logger.info("Form submission stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current submission status.
        
        Returns:
            Dict[str, Any]: Current status information
        """
        status = self._status_snapshot()
        elapsed_time = None
        if status["start_time"]:
            end_time = status["end_time"] or datetime.now()
            elapsed_time = int((end_time - status["start_time"]).total_seconds())
        
        completed = status["success"] + status["failed"]
        success_rate = 0
        if completed > 0:
            success_rate = (status["success"] / completed) * 100
        
        return {
            "running": status["running"],
            "total": status["total"],
            "completed": completed,
            "success": status["success"],
            "failed": status["failed"],
            "current_threads": status["current_threads"],
            "elapsed_time": elapsed_time,
            "success_rate": success_rate,
            "warning": status.get("warning")
        }
