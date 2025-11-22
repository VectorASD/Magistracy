from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time

s = Service('./chromedriver')

options = Options()
options.add_argument('start-maximized')

driver = webdriver.Chrome(service=s, options=options)
driver.implicitly_wait(10)


driver.get('https://lenta.com/catalog/frukty-i-ovoshchi')
# driver.refresh()

place = driver.find_element(By.CLASS_NAME, 'address-container__button')
place.click()

button = WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CLASS_NAME, 'delivery-flow__submit'))
)
button.click()
time.sleep(4)

while True:
    try:
        button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@modifiers = 'primary']"))
        )
        button.click()
    except TimeoutException:
        break

goods = driver.find_elements(By.CLASS_NAME, 'sku-card-small-container')
for good in goods:
    name = good.find_element(By.CLASS_NAME, 'sku-card-small-header__title').text
    print(name)


try:
    pass
except Exception as e:
    print(e)





