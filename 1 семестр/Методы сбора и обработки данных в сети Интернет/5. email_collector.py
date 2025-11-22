import asyncio
from pprint import pprint, pformat

from yandex_browser_driver import run_v2
from utils import timestamp_to_human, get_MongoDB_connection

from pymongo.errors import DuplicateKeyError # pip install pymongo[encryption]

DEBUG = False
if DEBUG:
    file = open("log.txt", "w", encoding="utf-8")

client = get_MongoDB_connection()
mails = client["email"]["mails"]

async def on_smart(response, page_unused):
    content = await response.json()
    body = content["body"]
    if not body: return
    threads = body["threads"]

    id2folder = {}
    for folder in body["folders"]:
        id2folder[int(folder["id"])] = folder

    for thread in threads:
        if thread["flags"].get("metathread", False): continue

        id          = thread["id"]
        date        = timestamp_to_human(thread["date"])
        folder_id   = int(thread["folder"])
        folder      = id2folder.get(folder_id, {"name": "???"})
        folder_name = folder["name"]
        size        = thread["size"]
        snippet     = thread["snippet"]
        subject     = thread["subject"]

        from_to     = thread["correspondents"]
        _from = tuple((sender["email"], sender["name"]) for sender in from_to["from"])
        to    = tuple((receiver["email"], receiver["name"]) for receiver in from_to["to"])
        assert len(_from) == 1
        # row = id, date, folder_id, folder_name, size, snippet, subject, _from[0], to
        doc = {
            "_id":     id,
            "date":    date,
            "folder": {
                "id": folder_id,
                "name": folder_name
            },
            "size":    size,
            "snippet": snippet,
            "from":    _from[0],
            "to":      to,
        }
        try: print("inserted:", mails.insert_one(doc)) # InsertOneResult(<uid>, acknowledged=True)
        except DuplicateKeyError: pass # самый быстрый способ, не создавая ещё одного запроса, проверить существование _id ;'-}

    if DEBUG:
        print(response, file=file)
        print(pformat(threads), file=file)
        print(file=file, flush=True)

def cb_factory(add_cb):
    add_cb("response", "https://e.mail.ru/api/v*/threads/status/smart?*", on_smart)

asyncio.run(run_v2("https://e.mail.ru", "cookies.asd", "cookies", cb_factory))
if DEBUG:
    file.close()

"""
Ссылка вида (убрал кучу несущественных дополняшек, но ссылка гораздо больше):
https://e.mail.ru/api/v1/threads/thread?quotes_version=1&id=ID_письма&email=ПОЧТА(достаётся из /index.html)&htmlencoded=false&token=ТОКЕН(достаётся из /index.html)
— это внутренний API Mail.ru, который используется самим веб‑клиентом (и мобильными приложениями) для работы с письмами.

id — идентификатор письма.
email — адрес ящика (берётся из index).
token — авторизационный токен (также из index).
Остальные параметры управляют форматом ответа.

📌 Разрешены ли автоматические запросы
Официально: такие API предназначены для работы только внутри веб‑клиента Mail.ru..
Правила платформы (Mail.ru Terms of Service) обычно запрещают автоматизированный доступ без их SDK или официальных API.
Использование внутренних API напрямую (через скрипты, боты, парсеры) может нарушать правила и привести к блокировке аккаунта.
Для интеграций Mail.ru предоставляет отдельные официальные API (например, Mail.ru Cloud API, API для рекламы и др.), но почтовый API в открытом виде не документирован.

📌 Итог
Технически — да, запросы работают, потому что это тот же механизм, что использует веб‑клиент.
Юридически — нет, автоматические запросы к этому API не разрешены правилами платформы, если они делаются вне официального клиента.
Безопасный путь — использовать только официальные SDK/API или IMAP/SMTP (они поддерживаются и предназначены для автоматизации).
"""

#   есть 2 варианта:
# либо, вручную открывать все письма, что впринципе законно, но 1000 с лишним писем (может вывалиться капча)...
# либо переходить на IMAP/SMTP, что уже ДАЛЕКО за пределами темы данного урока

# { $expr: { $gt: [ { $size: "$to" }, 1 ] } }
