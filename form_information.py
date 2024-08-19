from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class Field:
    def __init__(self, xpath: str, field_type: str, value: str = None):
        self.xpath = xpath
        self.field_type = field_type
        self.value = value

    def fill_field(self, driver):
        text_input = driver.find_element(By.XPATH, self.xpath)
        text_input.send_keys(self.value)

class Page:
    def __init__(self, fields: list[Field]):
        self.fields = fields
        self.num_fields = len(fields)

    def get_field(self, field_index: int):
        return self.fields[field_index]

    def fill_page(self,driver):
        for i in range(self.num_fields):
            self.get_field(i).fill_field(driver=driver)

class Form:
    def __init__(self, pages: list[Page], num_forms: int):
        self.pages = pages
        self.num_forms = num_forms
        self.num_pages = len(pages)

    def get_page(self, page_index: int) -> Page:
        return self.pages[page_index]
    
    def fill_form(self, driver):
        for i in range(self.num_pages-1):
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
            time.sleep(1)

            self.get_page(i).fill_page(driver=driver)

            button = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
            driver.execute_script("arguments[0].click();", button)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")))
            time.sleep(1)

            buttonlast = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")
            driver.execute_script("arguments[0].click();", buttonlast)
            print("check")
        except:
            print("error")

        print(i)
        try:
            WebDriverWait(driver, 2).until(EC.url_changes(driver.current_url))
        except:
            print("error 2")
        
        driver.quit()
