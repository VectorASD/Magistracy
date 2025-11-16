from lxml import html, etree
from time import time
import os
import pickle
from pprint import pprint, pformat
from io import StringIO
import json
import csv
from urllib.parse import urlparse

from utils import print_table, href_to_url_wrap, iso_to_human

import requests # pip install requests



class Cache:
    def __init__(self, path):
        self.path = path
        self.cache = cache = {}
        try:
            with open(path, "rb") as file:
                current_T = time()
                while True:
                    T, url, result = pickle.load(file)
                    if T >= current_T: cache[url] = result
        except (FileNotFoundError, EOFError): pass

    def load(self, url, time_to_life):
        try: result = self.cache[url]; print("from CACHE"); return result
        except KeyError: print("from NETWORK")

        response = requests.get(url)
        if not response.ok: # response.status_code not in range(200, 300):
            raise Exception(f"Loading URL error {response.status_code}: {response.text}")

        parsed = urlparse(response.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" # протокол + домен

        # response.encoding # уже в utf-8
        result = response.text, base_url
        self.store(time_to_life, url, result)
        return result

    def store(self, time_to_life, url, result):
        if url not in self.cache:
            obj = time() + time_to_life, url, result
            with open(self.path, "ab") as file:
                pickle.dump(obj, file, protocol=4)
            self.cache[url] = result

cache = Cache(os.path.join("cache", "lenta.asd"))



"""
// HTMLCollection багует из-за одновременной итерации и удаления элементов...
// Поэтому, используем [...collection], чтобы скопировать всё перед устранением
let count = 0;
for (const item of [...document.getElementsByClassName("card-big")]) {
    item.parentElement.removeChild(item);
    console.log(`removed(${++count}):`, item);
}
console.log("total removed:", count);

"card-feature" -> одна карточка
"card-big"     ->  52 карточки
"card-mini"    -> 107 карточек
"card-wide"    -> две карточки (без удаления с подсётом, скорее всего, я бы пропустил их)
"slider-video__slide" -> 20 видео

На сайте остались ещё "популярные видео", но, кроме href и картинки, там ничего интересного нет (но всё равно, я их добавил ;'-}).
Все перечисленные классы, кроме видео, содержат href, т.е. прямо самая основа блока.



Карточка будущего (огромная и обычно одна, но может быть несколько):

<a class="card-feature" href="/articles/2025/11/16/infections/">
    <div class="card-feature__image-wrap">
        <img class="card-feature__image" height="386" loading="lazy" src="https://icdn.lenta.ru/images/2025/11/14/14/20251114140638436/owl_feature_580_869676ad65b5f46f7c29ee0587ede4e6.jpg" width="580">
    </div>
    <div class="card-feature__topic">
        <h3 class="card-feature__title">Почти 200 россиян заразили гепатитом в онкоцентре, очаг нашли в кабинете КТ.</h3>
        <span class="card-feature__rightcol"> Как в России скрывали массовые вспышки болезней?</span>
        <div class="card-feature__info">
            <time class="card-feature__date">00:01</time>
        </div>
    </div>
</a>

Большая карточка:

<a class="card-big _longgrid" href="/articles/2025/11/16/legko/">
    <div class="card-big__image-wrap">
        <img class="card-big__image" height="186" loading="lazy" src="https://icdn.lenta.ru/images/2025/11/16/09/20251116095816773/owl_article_280_ae2ad2e76783ab22a2bf2f365c9369a1.jpg" width="280">
    </div>
    <div class="card-big__titles">
        <h3 class="card-big__title">«Тотальная доминация»</h3>
        <span class="card-big__rightcol"> Махачев победил Маддалену, забрав второй пояс UFC. Теперь он официально стал круче Нурмагомедова</span>
    </div>
    <div class="card-big__info">
        <time class="card-big__date">12:38</time>
    </div>
</a>

Маленькая карточка:

<a class="card-mini _longgrid" href="/news/2025/11/16/aliev-zayavil-o-zavershenii-stroitelstva-marshruta-trampa-na-territorii-azerbaydzhana/">
    <div class="card-mini__image-wrap"> ОПЦИОНАЛЬНО! Встречается только в <div class="sidebar">...</div>
        <img class="card-mini__image" height="40" loading="lazy" src="https://icdn.lenta.ru/images/2025/11/16/12/20251116124308324/owl_sq_40_276e541e3d049cf6c6de428bed990bd2.jpg" width="40">
    </div>
    <div class="card-mini__text">
        <h3 class="card-mini__title">Алиев заявил о завершении строительства «Маршрута Трампа» на территории Азербайджана</h3>
        <div class="card-mini__info">
            <time class="card-mini__info-item">14:12</time>
        </div>
    </div>
</a>

Имитация набора карточек (всего две):

<a class="card-wide _slider _dark _popular _photo" href="/articles/2025/11/04/glaskovo/">
    <div class="card-wide__image-wrap">
        <img class="card-wide__image" height="220" loading="lazy" src="https://icdn.lenta.ru/images/2025/07/09/13/20250709130019001/owl_article_big_330_b9602364d28bfd04e1151db12d621d6d.jpg" width="330">
    </div>
    <div class="card-wide__titles">
        <svg class="card-wide__photo-icon">
            <use xlink:href="#ui-photo"></use>
        </svg>
        <h3 class="card-wide__title">«Грабежи стали обычным явлением»</h3>
        <span class="card-wide__rightcol"> Как нацисты обращались с жителями советских деревень: уникальные кадры</span>
    </div>
</a>

Видеоролик:

<div class="slider-video__slide swiper-slide swiper-slide-visible swiper-slide-fully-visible" data-swiper-slide-index="3">
    <div class="slider-video__card js-video-explainer" id="record::e9903e99-3cf4-481a-b277-8fd508a7b9ea">
        <div class="slider-video__image-wrap">
            <img class="slider-video__image" height="360" loading="lazy" src="https://icdn.lenta.ru/images/2025/02/05/21/20250205213007924/preview_9665c1db942c1a44cda5522eaf388a39.jpg" width="640">
            <svg class="slider-video__icon">
                <use xlink:href="#ui-play"></use>
            </svg>
        </div>
    </div>
</div>
"""

def load_lenta(table):
    text, base_url = cache.load("https://lenta.ru/", 10 * 60)
    print("|text|:", len(text)) # 125207...
    href_to_url = href_to_url_wrap(base_url)

    tree = html.fromstring(text)
    sections = tree.xpath('//div[@class="main-page"]/section[@class="main-page__section"]')

    print("|sections|:", len(sections))
    for section in sections:
        cards = section.xpath('.//a[contains(@class,"card-feature") or '
                              'contains(@class,"card-big") or '
                              'contains(@class,"card-mini") or '
                              'contains(@class,"card-wide")]'
                              ' | .//div[contains(@class,"slider-video__card")]')
        print("  |cards|:", len(cards))

        for card in cards:
            href = href_to_url(card.xpath('./@href'))
            classes = tuple(name
                            for name in card.get("class", "").split()
                            if name.startswith("card-") or name.startswith("slider-video"))
            assert len(classes) == 1

            match classes[0]:
                case "card-feature":
                    title    = card.xpath('.//h3[@class="card-feature__title"]/text()')[0]
                    subtitle = card.xpath('.//span[@class="card-feature__rightcol"]/text()')
                    subtitle = subtitle[0].strip() if subtitle else None
                    date     = card.xpath('.//time[@class="card-feature__date"]/text()')[0]
                    image    = card.xpath('.//img[@class="card-feature__image"]/@src')[0]
                    row = "lenta.ru", "FEATURE", title, subtitle, date, image, href
                case "card-big":
                    title    = card.xpath('.//h3[@class="card-big__title"]/text()')[0]
                    subtitle = card.xpath('.//span[@class="card-big__rightcol"]/text()')
                    subtitle = subtitle[0].strip() if subtitle else None
                    date     = card.xpath('.//time[@class="card-big__date"]/text()')[0]
                    image    = card.xpath('.//img[@class="card-big__image"]/@src')[0]
                    row = "lenta.ru", "BIG", title, subtitle, date, image, href
                case "card-mini":
                    title    = card.xpath('.//h3[@class="card-mini__title"]/text()')[0]
                    date     = card.xpath('.//time[@class="card-mini__info-item"]/text()')
                    image    = card.xpath('.//img[@class="card-mini__image"]/@src')
                    date  = date[0]  if date  else None
                    image = image[0] if image else None
                    row = "lenta.ru", "MINI", title, None, date, image, href
                case "card-wide":
                    title    = card.xpath('.//h3[@class="card-wide__title"]/text()')[0]
                    subtitle = card.xpath('.//span[@class="card-wide__rightcol"]/text()')
                    subtitle = subtitle[0].strip() if subtitle else None
                    image    = card.xpath('.//img[@class="card-wide__image"]/@src')[0]
                    row = "lenta.ru", "WIDE", title, subtitle, None, image, href
                case "slider-video__card":
                    title = card.xpath('./@id')[0] # id видеоролика используем как title
                    image = card.xpath('.//img[@class="slider-video__image"]/@src')[0]
                    row = "lenta.ru", "VIDEO", title, None, None, image, None
                    # pprint(row)
            table.append(row)



def load_mail_news(table, pages = 8):
    text, base_url = cache.load("https://news.mail.ru/", 10 * 60)
    print("|text|:", len(text)) # 326738...
    href_to_url = href_to_url_wrap(base_url)

    tree = html.fromstring(text)
    items = tree.xpath('//div[@data-logger="news__FeedMainItem"]')
    print("  |items|:", len(items))
    for item in items:
        # print(etree.tostring(item, encoding="unicode", pretty_print=True))
        image  = item.xpath('.//picture[@data-qa="Picture"]/img/@src')[0]
        title  = item.xpath('.//h3[@data-qa="Title"]/a/text()')[0]
        teaser = item.xpath('.//div[@data-qa="Text"]/text()')[0].strip()
        category, source_text = item.xpath('.//span[@data-qa="Text"]/a[contains(@href,"/")]/span[@data-qa="Text"]/text()')
        source_link = href_to_url(item.xpath('.//a[@target="_blank"]/@href'))
        href        = href_to_url(item.xpath('.//h3[@data-qa="Title"]/a/@href'))

        subtitle = f"{category} ◯ {source_text} ({source_link}) ◯ {teaser}"
        date = iso_to_human(item.xpath('.//time/@datetime')[0])

        row = "news.mail.ru", "ARTICLE (0)", title, subtitle, date, image, href
        table.append(row)

    preload = tree.xpath('//script[@id="preload_news_main"]/text()')[0].split("=", 1)[1]
    obj = json.loads(preload)
    next_url = href_to_url(obj["news"]["actual"]["pager"]["next_url"])
    print("  next_url:", next_url)

    for page in range(1, pages):
        json_data, base_url = cache.load(next_url, 10 * 60)
        print("|json_data|:", len(json_data))
        href_to_url = href_to_url_wrap(base_url)

        obj = json.loads(json_data)["data"]
        next_url = href_to_url(obj["pager"]["next_url"])
        items    = obj["items"]

        print("  next_url:", next_url)
        print("  |items|:", len(items))
        for item in items:
            if item["content_type"] != "article":
                print("Странный content_type:", item["content_type"])
                pprint(item)
            picture  = item["picture"]
            image    = f'{picture["baseURL"]}{picture["uuid"]}/{picture["key"]}.{picture["fmt"][0]}'
            title    = item["title"]
            teaser   = item["description"]
            category = item["rubric"]["title"]
            source_text = item["source"]["title"]
            source_link = href_to_url(item["source"]["href"])
            href        = href_to_url(item["href"])

            subtitle = f"{category} ◯ {source_text} ({source_link}) ◯ {teaser}"
            date = iso_to_human(item["published"]["rfc3339"])

            row = "news.mail.ru", f"ARTICLE ({page})", title, subtitle, date, image, href
            table.append(row)

    # return pformat(obj)



if __name__ == "__main__":
    table = [("Сайт", "Тип блока", "Заголовок", "Описание", "Дата и время", "Картинка", "Ссылка")]
    load_lenta(table)
    add = load_mail_news(table)

    stream = StringIO()
    print_table(table, stream, middle_sep = False)

    with open("stdout3.txt", "w", encoding="utf-8") as file:
        file.write(stream.getvalue())
        # file.write(add)
    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(table, file, indent=4, ensure_ascii=False)
    with open("news.csv", "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        for row in table:
            writer.writerow(row)
