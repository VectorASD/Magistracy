from pprint import pprint, pformat
from lxml import html
import re
from io import StringIO
import json
from urllib.parse import urlsplit

from ASDsecrets import Storage
from utils import print_table

import requests # pip install requests

find_digits = re.compile(r'\d[\d\s\u202f]*').findall
find_currency = re.compile(r'(₽|\$|€|₴|₸|£|¥|₹|₦|₡|₱|₲|₵)').search
find_id = re.compile(r'/vacancy/(\d+)').search
"""
₽ — российский рубль
$ — доллар США
€ — евро
₴ — украинская гривна
₸ — казахстанский тенге
£ — британский фунт
¥ — китайский юань / японская иена
₹ — индийская рупия
₦ — нигерийская найра
₡ — коста‑риканский колон
₱ — филиппинское песо
₲ — парагвайский гуарани
₵ — ганский седи
"""

# Извлёк из скрипта сайта: nr = [[['EUR', '€'], '978'], [['USD', 'У\\.Е\\.', '\\$'], '840'], [['UAH', 'ГРН', '₴'], '980'], [['ТГ', 'KZT', '₸', 'ТҢГ', 'TENGE', 'ТЕНГЕ'], '398'], [['GBP', '£', 'UKL'], '826'], [['RUR', 'RUB', 'Р', 'РУБ', '₽', 'P', 'РUB', 'PУБ', 'PУB', 'PYБ', 'РYБ', 'РУB', 'PУБ'], '643']]
currency_code_to_symbol = {
    '€': '€', 'EUR': '€',
    '$': '$', 'USD': '$', 'У.Е.': '$',
    '₴': '₴', 'UAH': '₴', 'ГРН': '₴',
    '₸': '₸', 'KZT': '₸', 'ТГ': '₸', 'ТҢГ': '₸', 'TENGE': '₸', 'ТЕНГЕ': '₸',
    '£': '£', 'GBP': '£', 'UKL': '£',
    '₽': '₽', 'RUR': '₽', 'RUB': '₽', 'Р': '₽', 'РУБ': '₽', 'P': '₽', 'РUB': '₽', 'PУБ': '₽', 'PУB': '₽', 'PYБ': '₽', 'РYБ': '₽', 'РУB': '₽', 'PУБ': '₽',
}
# В языковом объекте (тоже, как часть скрипта сайта):
#            "vacancy.experience.between1And3": "1-3 года",
#            "vacancy.experience.between3And6": "3-6 лет",
#            "vacancy.experience.moreThan6": "более 6 лет",
#            "vacancy.experience.noExperience": "Без опыта",
# ...
#             "organization.form.0": "ООО",
#             "organization.form.1": "ОАО",
#             "organization.form.10": "Другое",
#             "organization.form.11": "ОДО",
# ...
#             "organization.form.60": "МВД",
experience_to_text = {
    "between1And3": "Опыт 1-3 года",
    "between3And6": "Опыт 3-6 лет",
    "moreThan6":    "Опыт более 6 лет",
    "noExperience": "Без опыта",
}
# arr = Array(61).fill("???")
# for (name in obj)
#     arr[parseInt(name.split(".")[2])] = obj[name];
# arr
form_id_to_text = (
    'ООО', 'ОАО', 'ЗАО', 'УП', 'ТОО', 'Нек. орг.', 'Общ. орг.', 'Фонд', 'Гос. корп.', 'ИП',
    'Другое', 'ОДО', 'Иностр. п.', 'Совместн. п.', 'Обществ. объед.', 'АО', 'ПАО', 'АНО', 'АУ', 'АТП',
    'МДОУ', 'ДОУ', 'БФ', 'БУ', 'ГБУ', 'ГКУ', 'ГП', 'ГУП', 'ГУЧ', 'ГБУЗ',
    'ФГБУЗ', 'ФБУЗ', 'ДОУч', 'КБ', 'МСЧ', 'МУП', 'МКП', 'МУУП', 'МУУЧ', 'МКУ',
    'МБУ', 'МУЧ', 'НПО', 'НПП', 'НТЦ', 'ПАТП', 'РО', 'СКБ', 'ТПП', 'ФГУП',
    'ФКП', 'ФБУ', 'ФГУ', 'ФГБУ', 'ФКУ', 'Министерство', 'Департамент', 'Администрация', 'Правительство', 'В/Ч',
    'МВД'
)



session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
})

storage = Storage("token.asd")
# storage.store({"uid": "hhuid", "token": "hhtoken"}, "secret", "hh_ru.asd")
store = storage.load("hh_ru.asd", "hh.ru uid+token")

# минимальные cookies
session.cookies.update({
    "hhuid": store["uid"],
    "hhtoken": store["token"],
    "regions": "4", # регион Новосибирск
})
# ym_uid, iap.uid, __ddg..., uxs_uid и т.п. - большинство служебные
# ym_*, __ddg*, device_breakpoint, cookie_policy_agreement, display=desktop - это аналитика и настройки интерфейса, их можно опустить

""" JSON-вариант:
url = "https://novosibirsk.hh.ru/shards/vacancy/search"
params = {
    "text": "программист C++",
    "salary": "",
    "ored_clusters": "true",
    "area": "4",
    "hhtmFrom": "vacancy_search_list",
    "hhtmFromLabel": "vacancy_search_line",
    "search_field": ["name", "company_name", "description"],
}
# data = resp.json()
# data = data["vacancySearchResult"]["vacancies"] (массив)
"""



NBSP = '\xa0' # chr(160)
def xpath_to_row(vac):
    title      = vac.xpath('.//span[@data-qa="serp-item__title-text"]/text()')
    link       = vac.xpath('.//a[@data-qa="serp-item__title"]/@href')
    company    = vac.xpath('.//span[@data-qa="vacancy-serp__vacancy-employer-text"]/text()')
    experience = vac.xpath('.//span[contains(@data-qa,"vacancy-serp__vacancy-work-experience")]/text()')
    address    = vac.xpath('.//span[@data-qa="vacancy-serp__vacancy-address"]/text()')

    assert len(title)      == 1
    assert len(link)       == 1
    assert len(company)    in (2, 4)
    assert len(experience) == 2 and experience[0] == experience[1]
    assert len(address)    == 4 and all(address[0] == address[i] for i in range(1, 4))

    comp_blocks = vac.xpath('.//div[starts-with(@class,"compensation-labels--")]')
    min_salary = max_salary = currency = None
    for block in comp_blocks:
        raw_text = block.xpath('string(.)').strip()
        # if "₽" in raw_text:
        cur_match = find_currency(raw_text)
        if cur_match:
            currency = cur_match.group(1)

            arr = tuple(int("".join(digits.split()))
                  for digits in find_digits(raw_text.split(currency, 1)[0]))
            assert len(arr) in (1, 2), (raw_text, arr)
            min_salary = arr[0]
            max_salary = arr[1] if len(arr) > 1 else float("inf")

    """
    print("~~~")
    print(title[0])
    print(link[0])
    print("".join(company[:len(company) // 2]).replace(NBSP, " "))
    if currency: print(min_salary, "-", max_salary, currency)
    print(experience[0])
    print(address[0])
    """
    row = title[0], link[0], "".join(company[:len(company) // 2]).replace(NBSP, " "), min_salary, max_salary, currency, experience[0], address[0], "hh.ru"
    return row

def json_to_row(vac, query):
    title      = vac["name"]
    link       = (vac["links"].get("desktop") or vac["links"].get("mobile")) + query
    company = vac["company"].get
    form_id = company("employerOrganizationFormId")
    form    = "" if form_id is None else form_id_to_text[form_id] + " "
    company    = form + (company("visibleName") or company("name"))
    experience = experience_to_text[vac["workExperience"]]
    address = vac.get("address", {}).get
    address    = (address("displayName")
                  or ", ".join(i for i in (address("city"), address("street"), address("building")) if i)
                  or vac["area"]["name"])

    compensation = vac["compensation"]
    currency = compensation.get("currencyCode", None)
    min_salary = compensation.get("from", None)
    max_salary = compensation.get("to", None)
    if currency:
        currency = currency_code_to_symbol[currency]
        if max_salary is None: max_salary = float("inf")
    """
    print("~~~")
    print(title)
    print(link)
    print(company)
    if currency: print(min_salary, "-", max_salary, currency)
    print(experience)
    print(address)
    """
    row = title, link, company, min_salary, max_salary, currency, experience, address, "hh.ru"
    return row

def load_page(table, text, page):
    url = "https://novosibirsk.hh.ru/search/vacancy"
    params = {
        "text": text,
        "salary": "",
        "ored_clusters": "true",
        "area": 4, # Новосибирск
        "hhtmFrom": "vacancy_search_list",
        "hhtmFromLabel": "vacancy_search_line",
    }
    if page > 0: params["page"] = page,

    resp = session.get(url, params=params)
    print(resp.status_code)
    print(resp.url)



    root = html.fromstring(resp.content)

    #vacancies = root.xpath('//div[contains(@class,"vacancy-info--")]')
    vacancies = root.xpath('//div[starts-with(@class,"vacancy-info--")]')
    print(f"|vacancies| (page {page}):", len(vacancies))
    for vac in vacancies:
        row = xpath_to_row(vac)
        id  = int(find_id(row[1]).group(1))
        table[id] = row

    query = ""
    if table:
        row = next(iter(table.values()))
        parts = urlsplit(row[1])
        if parts.query: query = "?" + parts.query

    # table.append(("~~~",) * 9)

    # add = [resp.text]
    template = root.xpath('//template[@id="HH-Lux-InitialState"]/text()')
    if template:
        data = json.loads(template[0])

        vacancies = data["vacancySearchResult"]["vacancies"]
        print(f"--> json |vacancies|:", len(vacancies))
        # |vacancies| (page 0): 20
        # --> json |vacancies|: 50
        # Приходим к тому выводу, что, сколько не используй xpath, но он здесь не нужен
        # т.к. всё равно, весь набор вакансий именно в json!
        # Достаточно url сменить на "https://novosibirsk.hh.ru/shards/vacancy/search",
        # как мы сразу будем получать этот HH-Lux-InitialState, без html

        # add.append(pformat(vacancies))
        for vac in vacancies:
            row = json_to_row(vac, query)
            id  = int(find_id(row[1]).group(1))
            table[id] = row

        print("account:", pformat(data["account"])) # email, firstName, lastName, middleName, phone
        # Все настоящие, все пятера от моего аккаунта, так что, куки работают!
        # Забавный факт: достаточно hhtoken, т.к. без hhuid работает точно также!
        # Если токена нет, все поля есть, но равны None (в json: null)

    pages = root.xpath('//a[@data-qa="pager-page"]/text()') # data-qa="pager-next" игнорирует
    max_page = max(int(page) for page in pages) if pages else 0
    return max_page



if __name__ == "__main__":
    table = {}

    page = 0
    while True:
        max_page = load_page(table, "Python", page)
        print("max_page:", max_page)
        page += 1
        if page > max_page: break
        print("~" * 77)

    table = (
        ("Вакансия", "URL", "Компания", "min_salary", "max_salary", "Валюта", "Опыт", "Адрес", "Сайт"),
        *(table[ID] for ID in sorted(table, reverse=True)),
    )
    print("max_page:", max_page)

    # import sys
    # print_table(table, sys.stdout)
    stream = StringIO()
    print_table(table, stream, middle_sep = False)
    # print(stream.getvalue())

    with open("stdout2.txt", "w", encoding="utf-8") as file:
        file.write(stream.getvalue())
        # for s in rc:
        #     file.write("\n")
        #     file.write(s)

# TODO: добавить поддержку сохранения json и csv
