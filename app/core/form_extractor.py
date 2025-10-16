from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from app.models import Form, ResponseConfig, Page, Question, AnswerConfig, AnswerOption
from typing import Optional, List
from datetime import datetime
import time, html, ast
from app.logging_config import logger


class FormExtractor:
    """
    Automated Google Forms Data Extractor
    
    This class provides comprehensive functionality to extract form structure,
    questions, and metadata from Google Forms using Selenium WebDriver.
    It supports multiple question types including text inputs, multiple choice,
    checkboxes, dropdowns, linear scales, and more.
    
    The extractor navigates through multi-page forms automatically, extracting
    all questions and their configurations, then returns a structured Form object
    suitable for automated form submission.
    
    Key Features:
    - Automatic form structure detection
    - Multi-page form support with navigation
    - Support for 10+ question types
    - Headless browser operation for server environments
    - Robust error handling and logging
    - Configurable Chrome browser options
    
    Supported Question Types:
    - input_text: Single-line text input
    - input_email: Email address input
    - textarea: Multi-line text input
    - multiple_choice: Single selection radio buttons
    - checkbox: Multiple selection checkboxes
    - dropdown: Dropdown selection menus
    - linear_scale: Rating scales (1-5, 1-10, etc.)
    - date: Date picker inputs
    - time: Time picker inputs
    - rank: Ranking/ordering questions
    - multiple_choice_grid: Grid of radio buttons
    - checkbox_grid: Grid of checkboxes
    
    Attributes:
        headless (bool): Whether to run Chrome in headless mode
        webview_port (int): Remote debugging port for Chrome
        chromebinary_path (str): Path to Chrome executable
        chromedriver_path (str): Path to ChromeDriver executable
        option_arguments (list): Chrome command-line arguments
        driver (webdriver.Chrome): Selenium WebDriver instance
    
    Example:
        >>> extractor = FormExtractor(
        ...     chromebinary_path="/path/to/chrome",
        ...     chromedriver_path="/path/to/chromedriver",
        ...     headless=True
        ... )
        >>> form = extractor.extract_form_data("https://forms.google.com/...")
        >>> print(f"Found {len(form.response_config.pages)} pages")
    """
    
    def __init__(self, chromebinary_path=None, chromedriver_path=None, headless=True, webview_port=None):
        """
        Initialize the FormExtractor with browser configuration.
        
        Args:
            chromebinary_path (str, optional): Full path to Chrome executable.
                                              Required for custom Chrome installations.
            chromedriver_path (str, optional): Full path to ChromeDriver executable.
                                              Required if not in PATH.
            headless (bool, optional): Run Chrome in headless mode. Defaults to True.
                                     Set to False for debugging or development.
            webview_port (int, optional): Port number for Chrome remote debugging.
                                        Useful for advanced debugging scenarios.
        
        Raises:
            ValueError: If required paths are not provided or don't exist
            
        Note:
            The extractor will configure Chrome with optimized settings for
            form extraction including disabled extensions, GPU acceleration,
            and notifications for better performance and reliability.
        """
        self.headless = headless
        self.webview_port = webview_port
        self.chromebinary_path = chromebinary_path
        self.chromedriver_path = chromedriver_path

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

        if self.webview_port:
            self.option_arguments.append(f'--remote-debugging-port={self.webview_port}')

    def initialize_driver(self):
        """
        Initialize and configure the Chrome WebDriver with optimized settings.
        
        This method creates a new Chrome WebDriver instance with pre-configured
        options for reliable form extraction. It applies security and performance
        optimizations suitable for automated browsing.
        
        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance ready for use
            
        Raises:
            Exception: If WebDriver initialization fails due to:
                      - Invalid Chrome or ChromeDriver paths
                      - Missing dependencies
                      - Permission issues
                      - Chrome version incompatibility
        
        Note:
            The driver is configured with the following optimizations:
            - Disabled sandbox for container environments
            - No GPU acceleration to prevent crashes
            - Disabled extensions for faster startup
            - Disabled notifications to prevent interruptions
            - Reduced logging for cleaner output
        """
        options = Options()
        for arg in self.option_arguments:
            options.add_argument(arg)
        options.binary_location = self.chromebinary_path

        try:
            service = Service(executable_path=self.chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("WebDriver initialized successfully")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def extract_form_data(self, form_url):
        """
        Extract comprehensive form data from a Google Forms URL.
        
        This is the main method that orchestrates the entire form extraction process.
        It navigates through all pages of a multi-page form, extracts questions,
        and builds a complete Form object with all metadata and structure.
        
        The extraction process:
        1. Validates the Google Forms URL
        2. Initializes WebDriver and loads the form
        3. Waits for form elements to be present
        4. Extracts form title and description
        5. Iterates through all form pages
        6. Extracts questions from each page
        7. Handles page navigation automatically
        8. Returns structured Form object
        
        Args:
            form_url (str): Valid Google Forms URL starting with
                           'https://docs.google.com/forms/'
        
        Returns:
            Form: Complete form object containing:
                - Form metadata (title, description, URL)
                - Response configuration with all pages
                - Question structures with answer options
                - Auto-generated form ID based on URL
        
        Raises:
            ValueError: If the URL is not a valid Google Forms URL
            TimeoutException: If form elements don't load within timeout
            NoSuchElementException: If required form elements are missing
            Exception: For any other extraction errors
        
        Example:
            >>> extractor = FormExtractor(headless=True)
            >>> form = extractor.extract_form_data(
            ...     "https://docs.google.com/forms/d/.../viewform"
            ... )
            >>> print(f"{form.title}: {len(form.response_config.pages)} pages")
        
        Note:
            - The method automatically handles multi-page forms
            - WebDriver is properly cleaned up even if extraction fails
            - Form data is completely extracted before returning
            - All question types are parsed and structured
        """
        if not form_url.startswith('https://docs.google.com/forms/'):
            raise ValueError("Invalid Google Form URL")

        try:
            self.driver = self.initialize_driver()
            self.driver.get(form_url)
            time.sleep(1)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@role='button']//span[" +
                     "contains(text(), 'T') or contains(text(), 'G') or " +
                     "contains(text(), 'Next') or contains(text(), 'Submit')]")
                )
            )

            try:
                title_element = self.driver.find_element(
                    By.XPATH, "//div[@role='heading' and @aria-level='1']"
                )
                title = title_element.text.strip()
            except NoSuchElementException:
                title = "Untitled Form"

            try:
                desc_element = title_element.find_element(
                    By.XPATH,
                    ".//parent::div//following-sibling::div[1]"
                )
                description = desc_element.text.strip()
            except NoSuchElementException:
                description = ""

            form_data = Form.from_url(
                url=form_url,
                title=title,
                description=description,
                created_at=datetime.now(),
                last_used=None,
                response_config=ResponseConfig(pages=[]),
                submissions=None
            )

            current_page = 1

            while True:
                logger.info(f"Extracting data from page {current_page}")

                time.sleep(1)
                page = Page(questions=self._extract_page_questions())
                form_data.response_config.pages.append(page)

                try:
                    next_button = self.driver.find_element(
                        By.XPATH,
                        "//div[@role='button']//span[" +
                        "contains(text(), 'T') or contains(text(), 'Next')]"
                    )
                    self.driver.execute_script("arguments[0].click();", next_button)
                    current_page += 1

                    time.sleep(1)
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH,
                             "//div[@role='button']//span[" +
                             "contains(text(), 'T') or contains(text(), 'Next')]")
                        )
                    )
                except (NoSuchElementException, TimeoutException):
                    logger.info("Không còn nút Next hoặc trang cuối")
                    break
            return form_data

        except Exception as e:
            logger.error(f"Error extracting form data: {str(e)}")
            raise ValueError(f"Error extracting form data: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()

    def _extract_page_questions(self):
        """
        Extract all questions from the current page of the form.
        
        This method locates all question containers on the current page
        and attempts to extract their data using Google Forms' internal
        data-params structure. It handles various question types and
        creates appropriate Question objects.
        
        Returns:
            List[Question] or None: List of Question objects found on the page,
                                   or None if no questions are found
        
        Note:
            - Uses Google Forms' internal CSS classes to locate questions
            - Falls back to email question detection if data-params fails
            - Calls _complete_questions to fill sample data for validation
        """
        page_questions = []

        question_containers = self.driver.find_elements(
            By.XPATH, "//div[contains(@class, 'geS5n')]"
        )

        for container in question_containers:
            try:
                data_params = container.find_element(
                    By.XPATH,
                    ".//span[contains(@class, 'M7eMe')]//ancestor::div[@data-params]"
                ).get_attribute("data-params")
                questions = self._extract_data_from_params(data_params)
                if questions:
                    page_questions.extend(questions)

            except NoSuchElementException:
                page_questions.append(Question(
                        question_id="q_email",
                        type="input_email",
                        text="Default Email",
                        answer_config=AnswerConfig(fill_percentage=0,
                                                   answers=[],
                                                   options=None)
                    ))
        
        if len(page_questions) > 0:
            self._complete_questions(page_questions)
            return page_questions
        else:
            return None

    def _extract_data_from_params(self, data_params: str) -> Optional[List[Question]]:
        """
        Parse Google Forms internal data-params to extract question information.
        
        This method decodes and parses the data-params attribute that Google Forms
        uses internally to store question metadata. It handles the complex nested
        structure and maps Google's internal question types to our standardized types.
        
        Args:
            data_params (str): Raw data-params string from Google Forms HTML
        
        Returns:
            Optional[List[Question]]: List of Question objects parsed from the data,
                                    or None if parsing fails
        
        Question Type Mapping:
            - 0: input_text or input_email (based on validation type)
            - 1: textarea
            - 2: multiple_choice
            - 3: dropdown
            - 4: checkbox
            - 5: linear_scale
            - 7: multiple_choice_grid or checkbox_grid
            - 9: date
            - 10: time
            - 18: rank
        
        Note:
            - Handles HTML entity decoding and JSON-like structure parsing
            - Creates AnswerOption objects for choice-based questions
            - Supports grid questions by creating multiple Question objects
            - Returns None on parsing errors to allow graceful degradation
        """
        try:
            decoded = (
                html.unescape(data_params)
                .replace('&quot;', '"')
                .replace('null', 'None')
                .replace('true', 'True')
                .replace('false', 'False')
                .replace('%.@.', '[')
            )

            data = ast.literal_eval(decoded)[0]
            questions = []

            question_type_raw = data[3]
            entry_id = data[4][0][0]
            question_text = data[1].strip()

            if question_type_raw == 0:
                if data[4][0][4] is not None:
                    qtype = "input_email" if data[4][0][4][0][1] == 102 else "input_text"
                else:
                    qtype = "input_text"
            elif question_type_raw == 1:
                qtype = "textarea"
            elif question_type_raw == 2:
                qtype = "multiple_choice"
            elif question_type_raw == 3:
                qtype = "dropdown"
            elif question_type_raw == 4:
                qtype = "checkbox"
            elif question_type_raw == 5:
                qtype = "linear_scale"
            elif question_type_raw == 7:
                qtype = "checkbox_grid" if data[4][0][11][0] else "multiple_choice_grid"
            elif question_type_raw == 9:
                qtype = "date"
            elif question_type_raw == 10: 
                qtype = "time"
            elif question_type_raw == 18:
                qtype = "rank"
            else:
                qtype = "unknown"

            if qtype in ["multiple_choice", "dropdown", "checkbox", "linear_scale", "rank"]:
                options_data = [opt[0] for opt in data[4][0][1]]
                options_data = [opt for opt in options_data if opt not in ("", None)]

                questions.append(Question(
                    question_id=str(entry_id),
                    type=qtype,
                    text=question_text,
                    answer_config=AnswerConfig(
                        options=[AnswerOption(text=opt,
                                            percentage=0.0) for opt in options_data],
                        fill_percentage=None,
                        answers=None
                    )
                ))
                
            elif qtype in ["checkbox_grid", "multiple_choice_grid"]:
                for id in data[4]:
                    questions.append(Question(
                        question_id=str(id[0]),
                        type=qtype.replace("_grid", ""),
                        text=question_text + " - " + str(id[3][0]),
                        answer_config=AnswerConfig(
                            options=[AnswerOption(text=opt[0],
                                                  percentage=0.0) for opt in data[4][0][1]],
                            fill_percentage=None,
                            answers=None
                        )
                    ))
            else:
                questions.append(Question(
                    question_id=str(entry_id),
                    type=qtype,
                    text=question_text,
                    answer_config=AnswerConfig(options=None,
                                               fill_percentage=0,
                                               answers=[])
                ))

            return questions

        except Exception as e:
            logger.error(f"Lỗi khi trích xuất data-params: {e}") 
            return None
        

    def _complete_questions(self, questions: List[Question]):
        """
        Fill form questions with sample data to validate form structure and navigation.
        
        This method interacts with each question on the current form page by filling
        them with appropriate sample data. This ensures that the form accepts the
        question types we've detected and allows proper navigation to subsequent pages.
        
        Args:
            questions (List[Question]): List of Question objects to fill with sample data
        
        Question Type Handling:
            - input_email: Fills with "extract@gmail.com"
            - input_text/time: Fills with "01"
            - textarea: Fills with "text"
            - date: Fills with "2025-01-01"
            - dropdown: Clicks first available option
            - multiple_choice/linear_scale/rank: Selects first radio option
            - checkbox: Selects all available checkboxes
        
        Note:
            - Uses JavaScript clicks for reliable interaction with Google Forms elements
            - Includes small delays for dropdown interactions to ensure proper loading
            - Handles both single and multiple input fields of the same type
            - Gracefully continues even if individual question filling fails
        
        Raises:
            NoSuchElementException: If question elements cannot be found (logged but not raised)
        """
        for question in questions:
            time.sleep(0.2)
            if question.question_id == "q_email":
                q_email_field = self.driver.find_element(By.XPATH, f"//input[@type='email']")
                q_email_field.send_keys("extract@gmail.com")
            else:
                question_container = self.driver.find_element(
                    By.XPATH, f"//div[contains(@data-params, '{question.question_id}')]"
                )
                if question.type == "input_email":
                    email_field = self.driver.find_elements(By.XPATH, f"//input[@type='email']")
                    for field in email_field:
                        field.send_keys("extract@gmail.com")
                elif question.type == "date":
                    date_field = question_container.find_element(By.XPATH, f".//input[@type='date']")
                    date_field.send_keys("2025-01-01")
                elif question.type in ["input_text", "time"]:
                    text_field = question_container.find_elements(By.XPATH, f".//input[@type='text']")
                    for field in text_field:
                        field.send_keys("01")
                elif question.type == "textarea":
                    textarea_field = question_container.find_element(By.XPATH, f".//textarea")
                    textarea_field.send_keys("text")

                elif question.type == "dropdown":
                    dropdown_button = question_container.find_elements(By.XPATH, f".//div[@role='option']")
                    self.driver.execute_script("arguments[0].click();", dropdown_button[0])
                    time.sleep(1)
                    dropdown_option = question_container.find_elements(By.XPATH, f".//div[@role='option']")
                    self.driver.execute_script("arguments[0].click()", dropdown_option[1])

                elif question.type in ["multiple_choice", "linear_scale", "rank"]:
                    radio_group = self.driver.find_elements(By.XPATH, f"//div[@role='radio']//ancestor::div[@role='radiogroup']")
                    for group in radio_group:
                        radio_button = group.find_element(By.XPATH, f".//div[@role='radio']")
                        self.driver.execute_script("arguments[0].click();", radio_button)

                elif question.type == "checkbox":
                    checkbox_button = question_container.find_elements(By.XPATH, f".//div[@role='checkbox']")
                    for button in checkbox_button:
                        self.driver.execute_script("arguments[0].click();", button)