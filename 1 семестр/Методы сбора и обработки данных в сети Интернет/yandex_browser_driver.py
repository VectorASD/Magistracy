import psutil

def find_yandex_browser_path():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['name'] and "browser" in proc.info['name'].lower():
                exe_path = proc.info['exe']
                if exe_path and "yandex" in exe_path.lower():
                    return exe_path
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

# C:\Program Files (x86)\Yandex\YandexBrowser\Application\browser.exe
browser_path = find_yandex_browser_path()



# selenium.common.exceptions.NoSuchDriverException: Message: Unable to obtain driver for chrome; For documentation on this error, please visit: https://www.selenium.dev/documentation/webdriver/troubleshooting/errors/driver_location
# На Windows можно скачать с https://chromedriver.chromium.org/downloads
# На Linux/macOS — через пакетный менеджер (apt install chromium-chromedriver, brew install chromedriver).

# chrome://version ->
# Yandex	138.0.7204.983 (64-разрядная версия)
# User Agent Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36

""" https://mirrors.huaweicloud.com/chromedriver/
138.0.7204.0/            27-May-2025 04:38 -
138.0.7204.15/           03-Jun-2025 22:49 -
138.0.7204.157/          14-Jul-2025 19:46 -
138.0.7204.168/          21-Jul-2025 23:10 -
138.0.7204.183/          28-Jul-2025 21:22 -
138.0.7204.2/            27-May-2025 18:04 -
138.0.7204.23/           10-Jun-2025 22:12 -
138.0.7204.35/           17-Jun-2025 22:11 -
138.0.7204.4/            27-May-2025 21:01 -
138.0.7204.49/           23-Jun-2025 22:54 -
138.0.7204.92/           27-Jun-2025 22:59 -
138.0.7204.94/           27-Jun-2025 23:07 -
"""

# Ссылка: https://mirrors.huaweicloud.com/chromedriver/138.0.7204.183/
# Скачиваем: chromedriver-win64.zip
# Распаковываем chromedriver.exe куда-нибудь

driver_path = "D:/Meow/chromedriver.exe" # Больше НЕ нужен!!! Это проблема selenium



""" Вариант не подходит, т.к. сильно косячит current_url
from selenium import webdriver # pip install selenium
from selenium.webdriver.chrome.service import Service
import time

options = webdriver.ChromeOptions()
options.binary_location = yandex_browser_path

service = Service(driver_path)

driver = webdriver.Chrome(service=service, options=options)
driver.get("https://ya.ru")
driver.execute_script("console.log('meow!')")

last_url = driver.current_url
while True:
    current_url = driver.current_url
    if current_url != last_url:
        print("URL изменился:", current_url)
        last_url = current_url
    time.sleep(0.1)
"""

from playwright.async_api import async_playwright # pip install playwright
import asyncio

async def run(url: str, cb):
    """
    Запускает браузер на указанном URL.
    При изменении URL вызывает cb(new_url).
    Если cb возвращает True, браузер закрывается и run завершается.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless        = False,
            executable_path = browser_path
        )
        page = await browser.new_page()
        await page.goto(url)

        stop_future = asyncio.Future()

        async def on_navigate(frame):
            new_url = frame.url
            try:
                result = cb(new_url)
                if result: # если callback вернул True
                    await browser.close()
                    if not stop_future.done():
                        stop_future.set_result(result)
            except Exception as e:
                print("Ошибка в callback:", e)

        page.on("framenavigated", on_navigate)

        return await stop_future

def test():
    # asyncio.run(run("https://ya.ru", lambda url: print("URL:", url)))
    def cb(url):
        if "#cat" in url: return "MEOW!"
    result = asyncio.run(run("https://ya.ru", cb))
    print("result:", result) # "MEOW!"
