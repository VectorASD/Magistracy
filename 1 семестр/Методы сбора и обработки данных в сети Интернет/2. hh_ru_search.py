from pprint import pformat
from lxml import html
import re
from io import StringIO

from ASDsecrets import Storage
from utils import print_table

import requests # pip install requests

find_digits = re.compile(r'\d[\d\s\u202f]*').findall
find_currency = re.compile(r'(₽|\$|€|₴|₸)').search



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

url = "https://novosibirsk.hh.ru/search/vacancy"
params = {
    "text": "программист C++",
    "salary": "",
    "ored_clusters": "true",
    "area": "4",
    "hhtmFrom": "vacancy_search_list",
    "hhtmFromLabel": "vacancy_search_line",
}

resp = session.get(url, params=params)
print(resp.status_code)
print(resp.url)



root = html.fromstring(resp.content)

#vacancies = root.xpath('//div[contains(@class,"vacancy-info--")]')
vacancies = root.xpath('//div[starts-with(@class,"vacancy-info--")]')
table = []
for vac in vacancies:
    title = vac.xpath('.//span[@data-qa="serp-item__title-text"]/text()')
    link = vac.xpath('.//a[@data-qa="serp-item__title"]/@href')
    company = vac.xpath('.//span[@data-qa="vacancy-serp__vacancy-employer-text"]/text()')
    experience = vac.xpath('.//span[contains(@data-qa,"vacancy-serp__vacancy-work-experience")]/text()')
    address = vac.xpath('.//span[@data-qa="vacancy-serp__vacancy-address"]/text()')

    assert len(title) == 1
    assert len(link) == 1
    assert len(company) in (2, 4)
    assert len(experience) == 2 and experience[0] == experience[1]
    assert len(address) == 4 and all(address[0] == address[i] for i in range(1, 4))

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
    print("".join(company[:len(company) // 2]))
    if currency: print(min_salary, "-", max_salary, currency)
    print(experience[0])
    print(address[0])
    """
    row = title[0], link[0], "".join(company[:len(company) // 2]), min_salary, max_salary, currency, experience[0], address[0]
    table.append(row)

# import sys
# print_table(table, sys.stdout)
stream = StringIO()
print_table(table, stream)
print(stream.getvalue())

# with open("stdout2.txt", "w", encoding="utf-8") as file:
#     file.write(pformat(vacancies))
