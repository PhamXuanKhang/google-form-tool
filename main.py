from form_information import *
from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
import random

class Main:
    def __init__(self):
        pass

    def input(self):
        field11 = Field(xpath="//input[@type='text' and @aria-labelledby='i1']", field_type="text", value="John")
        field12 = Field(xpath="//input[@type='text' and @aria-labelledby='i5']", field_type="text", value="Doe")
        field21 = Field(xpath="//textarea", field_type="text", value="Fill fill cai dmm")
        field22 = Field(xpath="//input[@type='date']", field_type="text", value="11102004")
        field311 = Field(xpath="//*[@id='mG61Hd']/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div[2]/div[1]/div/div[1]/input", field_type="text", value="01")
        field312 = Field(xpath="//*[@id='mG61Hd']/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[3]/div/div[1]/div/div[1]/input", field_type="text", value="02")
        page1 = Page([field11,field12])
        page2 = Page([field21,field22])
        page3 = Page([field311,field312])
        form = Form([page1,page2,page3], 10)
        return form
    
    def filling(self):
        form = self.input()
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        for i in range(form.num_forms):
            driver = webdriver.Chrome(options=options)
            driver.get(random.choice(['https://docs.google.com/forms/d/e/1FAIpQLSfQZ5Vb58GVbSIIUDM4GZiFQ4zbBys5xkEBgPZ0uwb7mj-RhQ/viewform?usp=pp_url&entry.2099488582=2024-08-07&entry.1137360084=02:01']))
            form.fill_form(driver=driver)