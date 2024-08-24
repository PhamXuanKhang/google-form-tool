from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from unidecode import unidecode
import random
import time

def gen_info(num_forms, field_types):
    ho_list = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Trịnh", "Lương", "Mai", "Tô", "Đinh", "Đào", "Vương", "Hà", "Thái"]
    ten_dem_list = ["Văn", "Thị", "Minh", "Đức", "Thành", "Tuấn", "Hữu", "Hoàng", "Thiện", "Như", "Kim", "Thu", "Ngọc", "Hải", "Quốc", "Gia", "Phương", "Thanh", "Bảo", "An", "Quyết", "Kiến", "Mỹ", "Duy", "Quỳnh"]
    ten_list = ["Anh", "Hương", "Nam", "Linh", "Hải", "Thảo", "Tùng", "Dương", "Thu", "Long", "Mai", "Hà", "Phong", "Trang", "Hoàng", "Lâm", "Bình", "Ngọc", "Thủy", "Trung", "Quang", "Lương", "Đăng", "Quốc", "Đạt"]

    # Gen name
    list_names = []
    for _ in range(num_forms):
        ho = random.choice(ho_list)
        ten_dem = random.choice(ten_dem_list)
        ten = random.choice(ten_list)
        list_names.append(f"{ho} {ten_dem} {ten}")

    # Gen email
    list_emails = []
    for name in list_names:
        arr = unidecode(name).split(" ")
        list_emails.append(f"{arr[2]}{arr[1]}{arr[0][0]}{random.randint(0,99999)}@gmail.com")

    if field_types.lower() == "name":
        return list_names
    elif field_types.lower() == "email":
        return list_emails
    
    elif field_types.lower() == "date":
        # Gen date
        list_dates = []
        for i in range(num_forms):
            list_dates.append(f"{random.randint(1999, 2005)}-{random.randint(1, 12)}-{random.randint(1, 28)}")
        return list_dates
    
    elif field_types.lower() == "phone":
        # Gen phone
        list_phones = []
        for _ in range(num_forms):
            list_phones.append(f"09{random.randint(10000000, 99999999)}")
        return list_phones
    
    elif field_types.lower() == "other":
        return ["" for i in range(num_forms)]

# Field class for fill each field
class Field:
    def __init__(self, xpath: str, field_type: str, value: str = None):
        self.xpath = xpath
        self.field_type = field_type
        self.value = value.split("\n")
        self.full_value = list(self.value)

    def prepare_full_value(self, num_forms):
        if len(self.value) == len(self.full_value):
            self.full_value.extend(gen_info(num_forms, self.field_type))
            self.full_value = self.full_value[:num_forms]
            random.shuffle(self.full_value)

    def fill_field(self, driver, state_num):
        text_input = driver.find_element(By.XPATH, self.xpath)
        text_input.send_keys(self.full_value[state_num])

# Page class for field each page
class Page:
    def __init__(self, fields: list[Field]):
        self.fields = fields
        self.num_fields = len(fields)

    def get_field(self, field_index: int):
        return self.fields[field_index]

    def fill_page(self,driver, num_forms, state_num):
        for i in range(self.num_fields):
            self.get_field(i).prepare_full_value(num_forms=num_forms)
            self.get_field(i).fill_field(driver=driver, state_num=state_num)

# Form class
class Form:
    def __init__(self, pages: list[Page], num_forms: int, links: str, money: int):
        self.pages = pages
        self.num_forms = num_forms
        self.num_pages = len(pages)
        self.links = links
        self.money = money

    def get_page(self, page_index: int) -> Page:
        return self.pages[page_index]
    
    def fill_form(self, driver, state_num):
        for i in range(self.num_pages-1):
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
                time.sleep(1)

                self.get_page(i).fill_page(driver=driver, num_forms=self.num_forms, state_num=state_num)

                button = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
                driver.execute_script("arguments[0].click();", button)
            except Exception as e:
                print(e)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")))
            time.sleep(1)

            self.get_page(self.num_pages-1).fill_page(driver=driver, num_forms=self.num_forms, state_num=state_num)

            buttonlast = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")
            driver.execute_script("arguments[0].click();", buttonlast)
        except Exception as e:
            print(e)

        try:
            WebDriverWait(driver, 2).until(EC.url_changes(driver.current_url))
        except:
            print("Filled")
        
        driver.quit()

    def get_num_fields(self):
        return sum([len(self.pages[i].fields) for i in range (self.num_pages)])