from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
        
option_arguments = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-extensions', '--disable-gpu', '--disable-notifications', '--log-level=3', '--headless']

def initialize_driver(binary_path, driver_path, option_arguments):
    options = Options()
    for arg in option_arguments:
        options.add_argument(arg)
    options.binary_location = binary_path
    service = Service(executable_path=driver_path)
    return webdriver.Chrome(service=service, options=options)