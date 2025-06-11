from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class FormProcessor:
    def __init__(self):
        self.option_arguments = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-extensions', '--disable-gpu', '--disable-notifications', '--log-level=3', '--headless']
        self.binary_path = '/drivers/chrome'
        self.driver_path = '/drivers/chromedriver'

def extract_form_data(form_url):
    # """
    
    # Args:
    #     form_url (str): URL của Google Form.
    
    # Returns:
    #     list: Danh sách các câu hỏi với thông tin (question, type, options, percentages, answer).
    # """
    # options = Options()
    # for arg in self.option_arguments:
    #     options.add_argument(arg)
    # options.binary_location = self.binary_path
    # service = Service(executable_path=self.driver_path)
    # driver = webdriver.Chrome(service=service, options=options)
    
    # driver.get(form_url)




    form_data = [
        {
            'question': 'What is your favorite color?',
            'type': 'multiple_choice',
            'options': ['Red', 'Blue', 'Green'],
            'percentages': [0, 0, 0]
        },
        {
            'question': 'How often do you exercise?',
            'type': 'dropdown',
            'options': ['Daily', 'Weekly', 'Rarely'],
            'percentages': [0, 0, 0]
        },
        {
            'question': 'Describe your experience',
            'type': 'text',
            'options': [],
            'percentages': [],
            'answer': ''
        }
    ]
    return form_data
    