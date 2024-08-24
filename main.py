from form_information import *
from selenium import webdriver
import threading
import random
import csv

""" Main structure to run fill action"""
class Main:
    def __init__(self, form):
        self.is_run = False 
        self.is_fair = False
        self.form = form
        self.state_num = 0
        self.time = 0
        self.lock = threading.Lock()
        self.thread = None
    
    def start_fill(self):
        if self.thread is None or not self.thread.is_alive():
            self.is_run = True  # Start run
            self.form.links = self.form.links.split("\n")
            self.thread = threading.Thread(target=self.process_forms)
            self.thread.start()
    
    def process_forms(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        while self.state_num < self.form.num_forms:
            with self.lock:
                start_time = time.time()

                if not self.is_run:
                    break  # Break immediately if stop

                driver = webdriver.Chrome(options=options)
                if self.is_fair:
                    driver.get(self.form.links[self.state_num % len(self.form.links)])
                else:
                    driver.get(random.choice(self.form.links))

                self.form.fill_form(driver=driver, state_num=self.state_num)
                self.state_num += 1

                end_time = time.time()
                elapsed_time = end_time - start_time
                self.time += elapsed_time

        if self.state_num == self.form.num_forms:
            self.save_to_csv()

    def stop_fill(self):
        self.is_run = False  # Only change status to stop process
    
    def continue_fill(self):
        if not self.is_run:  # Only continue if stopped
            self.is_run = True
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self.process_forms)
                self.thread.start()

    # Save data to excel
    def save_to_csv(self):
        with open("form_data.csv", "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([self.form.num_pages, self.form.num_forms, self.time, self.form.get_num_fields(), self.form.money])