import json
import re
from pprint import pprint, pformat
from io import StringIO

from utils import print_table, get_MongoDB_connection



def get_base(client, name):
    # print(client.list_database_names())
    # Так, СТОП!!! Процесса создания баз данных и таблиц в них нет?!)))
    return client[name]

def first_steps():
    # print(client.list_database_names()) # ['admin', 'config', 'local'] (как и в "компасе")
    # db = client["admin"]
    # print(db.list_collection_names()) # ['system.version']

    db = get_base(client, "jobs_db")
    vacancies = db["vacancies"]
    print(vacancies.insert_one({"title": "Test Vacancy"})) # InsertOneResult(ObjectId('691aeca0bca9704e4142f7ea'), acknowledged=True)
    # в компасе всегда видно параметр "_id", он и содержит то, что указано в ObjectId

find_id = re.compile(r"/vacancy/(\d+)").search
def extract_id(url):
    m = find_id(url)
    assert m
    return int(m.group(1))
    # "https://novosibirsk.hh.ru/vacancy/(\d+)?query=Python&hhtmFrom=vacancy_search_list"

def row2doc(uid, row):
    title, href, company, min_salary, max_salary, currency, experience, address, source = row
    return {
        "_id":        uid,
        "title":      title,
        "href":       href,
        "company":    company,
        "min_salary": min_salary,
        "max_salary": float("inf") if max_salary == "inf" else max_salary,
        "currency":   currency,
        "experience": experience,
        "address":    address,
        "source":     source,
    }

def doc2row(doc):
    return (
        doc["title"],
        doc["href"],
        doc["company"],
        doc["min_salary"],
        doc["max_salary"],
        doc["currency"],
        doc["experience"],
        doc["address"],
        doc["source"],
    )

def insert_vacancy(vacancies, row):
    href = row[1]
    uid = extract_id(href) # unique_id
    if vacancies.find_one({"_id": uid}): return False

    doc = row2doc(uid, row)
    print("inserted:", vacancies.insert_one(doc)) # InsertOneResult(<uid>, acknowledged=True)
    return True

exchange_rates = { # в реальном проекте, желательно, подгружать это через API
    '₽': 1,   # российский рубль
    '$': 100, # доллар США
    '€': 110, # евро
    '₴': 2.5, # украинская гривна
    '₸': 0.2, # казахстанский тенге
    '£': 130, # британский фунт
}

def find_by_salary(vacancies, header, amount, currency = '₽'):
    amount *= exchange_rates[currency]
    # q - query
    q = {"$or": tuple(
      {"$and": (
        {"currency": symbol},
        {"min_salary": {"$lte": amount * mul}},
        #{"$or": (
          {"max_salary": {"$gte": amount * mul}},
        #  {"max_salary": None},
        #)}
      )} for symbol, mul in exchange_rates.items()
    )}
    # pprint(q) # красиво выглядит ;'-}
    response = vacancies.find(q)
    table = (
        header,
        *(doc2row(doc) for doc in response)
    )
    return q, table



client = get_MongoDB_connection()

db = get_base(client, "jobs_db")
vacancies = db["vacancies"]

with open("vacancies.json", "rb") as file:
    table = json.load(file)

it = iter(table)
header = next(it)

print("Всего записей:", len(table) - 1)
count = sum(insert_vacancy(vacancies, row) for row in it)
print("Вставлено новых записей:", count)

# q, table = find_by_salary(vacancies, header, 250000)
q, table = find_by_salary(vacancies, header, 2500, '$')

stream = StringIO()
print_table(table, stream, middle_sep = False)

pprint(q)
print(stream.getvalue())

with open("stdout4.txt", "w", encoding="utf-8") as file:
    file.write(pformat(q))
    file.write('\n')
    file.write(stream.getvalue())
