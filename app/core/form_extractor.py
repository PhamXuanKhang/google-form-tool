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
    def __init__(self, chromebinary_path=None, chromedriver_path=None, headless=True, webview_port=None):
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
                    WebDriverWait(self.driver, 10).until(
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
        for question in questions:
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
                    self.driver.execute_script("arguments[0].click(); arguments[1].click();", dropdown_option[1], dropdown_option[1])


                elif question.type in ["multiple_choice", "linear_scale", "rank"]:
                    radio_group = self.driver.find_elements(By.XPATH, f"//div[@role='radio']//ancestor::div[@role='radiogroup']")
                    for group in radio_group:
                        radio_button = group.find_element(By.XPATH, f".//div[@role='radio']")
                        self.driver.execute_script("arguments[0].click();", radio_button)
                elif question.type == "checkbox":
                    checkbox_button = question_container.find_elements(By.XPATH, f".//div[@role='checkbox']")
                    for button in checkbox_button:
                        self.driver.execute_script("arguments[0].click();", button)