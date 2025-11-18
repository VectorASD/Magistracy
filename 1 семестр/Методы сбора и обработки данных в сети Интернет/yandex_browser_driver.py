import psutil
from pprint import pprint

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
# На Windows можно скачать с https://mirrors.huaweicloud.com/chromedriver/
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



import asyncio

from ASDsecrets import Storage

from playwright.async_api import async_playwright # pip install playwright



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



storage = Storage("token.asd")
# storage.to_force("cookies.asd", "cookies")

async def run2(url: str):
    COOKIE_LOG = False

    if COOKIE_LOG:
        file = open("log.txt", "w", encoding="utf-8")
        def log(*a, **b):
            print(*a, **b)
            print(*a, **b, file=file, flush=True)

    def cookie_key(cookie):
        # Берём только стабильные поля (игнорируем "expires")
        return (
            cookie["domain"],
            cookie["path"],
            cookie["name"],
            cookie["value"],
            cookie.get("httpOnly", False),
            cookie.get("secure", False),
            cookie.get("sameSite", "None"),
        )

    prev_cookies = []
    async def monitor_cookies(ctx, interval=5):
        nonlocal prev_cookies
        prev = set(cookie_key(cookie) for cookie in prev_cookies)
        while True:
            cookies = await ctx.cookies()
            if cookies != prev_cookies:
                prev_cookies = cookies
                storage.store(cookies, None, "cookies.asd", "cookies")

                if COOKIE_LOG:
                    log("Куки изменились!")
                    prev_upd = set()
                    for cookie in cookies:
                        key = cookie_key(cookie)
                        if key in prev: prev.discard(key)
                        else: log("+", key)
                        prev_upd.add(key)
                    for cookie in prev:
                        log("-", cookie)
                    prev = prev_upd
            await asyncio.sleep(interval)

    def on_close(page):
        # print("Closed:", page)
        # print("Осталось:", len(ctx.pages))
        if not ctx.pages:
            stop_future.set_result(True)

    def on_request(req):
        cookies = req.headers.get("cookie", ())
        # print(f"C: {len(cookies)} {req.method} {req.url}"[:160])
        if cookies:
            log = f"C: {cookies}\n"
            #print(log)
            #file.write(log)

    def on_response(resp):
        cookies = resp.headers.get("set-cookie", 0)
        # print(f"S: {cookies} {resp.url} {resp.status}"[:160])
        if resp.headers:
            log = f"S: {resp.url} {resp.status} {resp.headers}\n"
            #print(log)
            #file.write(log)

    def on_page(page):
        # print("Новое окно:", page.url)
        page.on("close", on_close)
        page.on("request", on_request)
        page.on("response", on_response)

    stop_future = asyncio.Future()

    cookies = storage.load("cookies.asd", "cookies")
    if False:
        pprint(sorted((cookie["name"], cookie["domain"]) for cookie in cookies))
        exit()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless        = False,
            executable_path = browser_path
        )

        ctx = await browser.new_context()
        ctx.on("page", on_page)

        if cookies:
            await ctx.add_cookies(cookies)
            prev_cookies = cookies
        asyncio.create_task(monitor_cookies(ctx, interval=0.1))

        page = await ctx.new_page() # именно это добавляет в browser.contexts первый контекст
        # ctx = browser.contexts[0] # аналог browser.new_context()

        # print(ctx.pages) # [<Page url='about:blank'>]
        asyncio.create_task(page.goto(url))
        # print(ctx.pages) # [<Page url='https://mail.ru/'>] (при использовании await для page.goto)

        await stop_future
        await p.stop()

    if COOKIE_LOG:
        file.close()



if __name__ == "__main__":
    asyncio.run(run2("https://e.mail.ru"))
