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
from app.logging_config import logger

import threading
import time
import random
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
        
        self.status = {
            "running": False,
            "total": 0,
            "success": 0,
            "failed": 0,
            "current_threads": 0,
            "start_time": None,
            "end_time": None,
            "success_rate": 0,
            "warning": None
        }
        
        self.stop_flag = threading.Event()
        self.threads = []
        
        self.form_processor = FormProcessor(self.form)
        
        self.option_arguments = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-notifications',
            '--log-level=3'
        ]
        
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
            service = Service(executable_path=self.chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def submit_form(self,
                    num_submissions: int = 1,
                    concurrent_threads: int = 1,
                    min_delay: int = 1,
                    max_delay: int = 5,
                    responses: Optional[Dict[str, Any]] = None,
                    responses_list: Optional[List[Dict[str, Any]]] = None,
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
        # Data-driven mode: each item in responses_list is one submission
        if responses_list:
            num_submissions = len(responses_list)
            self.responses_queue = list(responses_list)
            self.responses_lock = threading.Lock()
            self.data_driven_mode = True
        else:
            self.responses_queue = None
            self.data_driven_mode = False

        # Reset status
        self.status = {
            "running": True,
            "total": num_submissions,
            "success": 0,
            "failed": 0,
            "current_threads": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "success_rate": 0,
            "warning": None
        }

        self.stop_flag.clear()

        # Generate responses if not provided (for non-data-driven mode)
        if not self.data_driven_mode:
            self.responses = responses or self.form_processor.generate_random_responses()

        # Start submission threads
        for i in range(min(concurrent_threads, num_submissions)):
            submissions_per_thread = num_submissions // concurrent_threads

            if i < num_submissions % concurrent_threads:
                submissions_per_thread += 1

            thread = threading.Thread(
                target=self._submission_worker,
                args=(submissions_per_thread, min_delay, max_delay, callback)
            )
            self.threads.append(thread)
            thread.start()
            self.status["current_threads"] += 1
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()
        
        # Update final status
        self.status["running"] = False
        self.status["end_time"] = datetime.now()
        
        if self.status["total"] > 0:
            self.status["success_rate"] = (self.status["success"] / self.status["total"]) * 100

        if self.status["success_rate"] < HIGH_FAILURE_WARNING_THRESHOLD:
            self.status["warning"] = HIGH_FAILURE_WARNING_MESSAGE
            logger.warning(
                f"{HIGH_FAILURE_WARNING_MESSAGE} Success rate: {self.status['success_rate']:.2f}% "
                f"({self.status['success']}/{self.status['total']})"
            )
        else:
            self.status["warning"] = None
        
        # Create submission record
        time_used = 0
        if self.status["start_time"] and self.status["end_time"]:
            time_used = int((self.status["end_time"] - self.status["start_time"]).total_seconds())
        
        submission = Submission(
            num_submission=self.status["total"],
            concurrent_thread=concurrent_threads,
            time_used=time_used,
            success_rate=self.status["success_rate"],
            network_status="Completed"
        )
        
        logger.info(f"Form submission completed: {submission.submission_id}")
        logger.info(f"Success rate: {submission.success_rate:.2f}% ({self.status['success']}/{self.status['total']})")
        
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
                    self.status["success"] += 1
                else:
                    self.status["failed"] += 1

                if callback:
                    callback(success)

                # Random delay between submissions
                if _ < num_submissions - 1 and not self.stop_flag.is_set():
                    delay = random.uniform(min_delay, max_delay)
                    time.sleep(delay)
        
        except Exception as e:
            logger.error(f"Error in submission worker: {str(e)}")
        
        finally:
            self.status["current_threads"] -= 1
            if driver:
                driver.quit()
    
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
            driver.get(self.form.url)
            
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
                    # Look for Next button
                    next_button = driver.find_element(
                        By.XPATH,
                        "//div[@role='button']//span[contains(text(), 'Next') or contains(text(), 'Tiếp')]"
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    current_page += 1
                    
                    # Wait for next page to load
                    time.sleep(1)
                    
                except NoSuchElementException:
                    # If no Next button, look for Submit button
                    try:
                        submit_button = driver.find_element(
                            By.XPATH,
                            "//div[@role='button']//span[contains(text(), 'Submit') or contains(text(), 'Gửi')]"
                        )
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
                    # Click dropdown to open it
                    dropdown = question_container.find_element(By.XPATH, ".//div[contains(@role, 'listbox')]")
                    driver.execute_script("arguments[0].click();", dropdown)
                    time.sleep(0.5)
                    
                    # Find and click the option matching our response
                    options = driver.find_elements(By.XPATH, f"//div[@role='option']//span[text()='{response}']")
                    if options:
                        driver.execute_script("arguments[0].click();", options[0])
                    else:
                        # If exact match not found, click first option
                        first_option = driver.find_element(By.XPATH, "//div[@role='option']")
                        driver.execute_script("arguments[0].click();", first_option)
                
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
        
        self.status["running"] = False
        self.status["end_time"] = datetime.now()
        
        logger.info("Form submission stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current submission status.
        
        Returns:
            Dict[str, Any]: Current status information
        """
        # Calculate elapsed time
        elapsed_time = None
        if self.status["start_time"]:
            end_time = self.status["end_time"] or datetime.now()
            elapsed_time = int((end_time - self.status["start_time"]).total_seconds())
        
        # Calculate current success rate
        success_rate = 0
        if self.status["success"] + self.status["failed"] > 0:
            success_rate = (self.status["success"] / (self.status["success"] + self.status["failed"])) * 100
        
        return {
            "running": self.status["running"],
            "total": self.status["total"],
            "completed": self.status["success"] + self.status["failed"],
            "success": self.status["success"],
            "failed": self.status["failed"],
            "current_threads": self.status["current_threads"],
            "elapsed_time": elapsed_time,
            "success_rate": success_rate,
            "warning": self.status.get("warning")
        }
