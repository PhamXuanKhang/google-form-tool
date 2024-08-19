from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

options = webdriver.ChromeOptions()
options.add_argument("--headless")

j = 0 # control link
for i in range(200):    # Số lượt chạy
    # driver = webdriver.Chrome()
    driver = webdriver.Chrome(options = options)     # Khởi tạo trình duyệt

    driver.get(random.choice(list_link))        #Mở Google Form
    # driver.get(list_link[j])
    # j+=1
    # if j>9:
    #     j = 0

    # tiếp lần 1
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
    time.sleep(1)
    # text_input1 = driver.find_element(By.XPATH, "//input[@type='text' and @aria-labelledby='i1']")
    # text_input1.send_keys(list_phone[i])
    # text_input2 = driver.find_element(By.XPATH, "//input[@type='text']")
    # text_input2.send_keys(list_mail[i])
    button = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
    driver.execute_script("arguments[0].click();", button)

    # # tiếp lần 2
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
    # time.sleep(1)
    # button2 = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
    # driver.execute_script("arguments[0].click();", button2)

    # # tiếp lần 3
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
    # time.sleep(1)
    # # text_input = driver.find_element(By.XPATH, "//input[@type='text']")
    # # text_input.send_keys(list_idea[i])
    # button3 = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
    # driver.execute_script("arguments[0].click();", button3)

    # # tiếp lần 4
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")))
    # time.sleep(1)
    # button4 = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'Tiếp')]")
    # driver.execute_script("arguments[0].click();", button4)

    # gửi
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")))
        time.sleep(1)
        text_input3 = driver.find_element(By.XPATH, "//input[@type='text' and @aria-labelledby='i78']")
        text_input3.send_keys(list_advice[i])
        # text_input4 = driver.find_element(By.XPATH, "//input[@type='text' and @aria-labelledby='i53']")
        # text_input4.send_keys(list_advice[i])
        buttonlast = driver.find_element(By.XPATH, "//div[@role='button']//span[contains(text(), 'G')]")
        driver.execute_script("arguments[0].click();", buttonlast)
        print("check")
    except:
        continue

    print(i)
    try:
        WebDriverWait(driver, 2).until(EC.url_changes(driver.current_url))
    except:
        continue

    # Đóng trình duyệt
    driver.quit()