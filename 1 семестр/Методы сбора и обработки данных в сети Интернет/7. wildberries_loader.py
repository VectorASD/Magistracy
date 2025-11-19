import asyncio
from pprint import pprint, pformat
import os
import json

from yandex_browser_driver import run_v2
import requests

# log = open("log.txt", "w")
session = requests.Session()

sem = asyncio.Semaphore(16) # максимум 16 fetch-задач одновременно
# 853 файла - 100 папок = 753 картинки за раз! Нужен ограничитель, а то страница крашется от нехватки памяти ;'-}
# сколько папок, столько и data.json файлов... остальное - картинки *.webp

async def limited_fetch(page, url):
    async with sem:
        return await page.evaluate(f'fetch("{url}", {{ mode:"no-cors", cache:"force-cache" }})')

async def load_images(page, img_url: str, workdir: str, pics: int):
    for i in range(1, pics + 1):
        img_path = os.path.join(workdir, f"{i}.webp")
        if not os.path.exists(img_path):
            # asyncio.create_task(page.evaluate(f'console.log("{img % i}")'))
            asyncio.create_task(limited_fetch(page, img_url % i))

async def on_search(response, page):
    content = await response.json()
    if "products" not in content: return # зато здесь есть content["data"]["filters"] (массив типа list)

    category = content["metadata"]["name"].split(" ", 1)[-1].capitalize()
    print(f'{category}: {content["total"]} товаров')

    products = content["products"]
    # print("~" * 77, file=log)
    # print(pformat(products), file=log)

    print("|products|:", len(products))
    for product in products:
        id      = product["id"]
        img_url = id2image(id)
        workdir = os.path.join("7. products", str(id))
        pics    = int(product["pics"])

        os.makedirs(workdir, exist_ok=True)
        asyncio.create_task(load_images(page, img_url, workdir, pics))

        with open(os.path.join(workdir, "data.json"), "w", encoding="utf-8") as file:
            json.dump(product, file, ensure_ascii=False, indent=4, sort_keys=True)

async def on_image(response, page):
    split = response.url[8:].split("/")
    id   = int(split[3])
    name = split[-1]
    path = os.path.join("7. products", str(id), name)
    if not os.path.exists(path):
        body = await response.body()
        print(response.status, id, name, len(body), "b.")
        with open(path, "wb") as file:
            file.write(body)

def cb_factory(add_cb):
    # https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search?
    # https://www.wildberries.ru/__internal/u-search/exactmatch/ru/common/v18/search?
    add_cb("response", "https://www.wildberries.ru/__internal/*search/exactmatch/ru/common/v*/search?*", on_search)
    add_cb("response", "https://basket-??.wbbasket.ru/vol*/part*/*/images/c*x*/*.*",                     on_image)
    add_cb("response", "https://ekt-basket-cdn-??.geobasket.ru/vol*/part*/*/images/c516x688/*.*",        on_image)



""" Здесь нашёл интересную штуку: https://static-basket-01.wbbasket.ru/vol0/data/settings-front.json
{
    "BYN": {"rubRate": 27.3047},
    "KZT": {"rubRate": 0.155361},
    "AMD": {"rubRate": 0.212192},
    "KGS": {"rubRate": 0.925612},
    "UZS": {"rubRate": 0.0067789},
    "AZN": {"rubRate": 47.6146},
    "GEL": {"rubRate": 29.8932},
    "TJS": {"rubRate": 8.72043},
    "TMT": {"rubRate": 23.1271},
    "USD": {"rubRate": 80.9448},
    "RUB": {"rubRate": 1}
}
"""



# https://basket-15.wbbasket.ru/vol2282/part228273/228273618/images/c516x688/1.webp
# https://basket-??.wbbasket.ru/vol*/part*/*/images/c*x*/1.*
# как нетрудно догадаться, все 4 числа исходят из идентификатора товара
# поддерживаемые размеры: "tm", "c246x328", "c516x688", tm даёт 75x100
# поддерживаемые форматы: ".jpg", ".webp" (.jpg может и не быть)

"""
start(e, t) {
    return this.timer && (this.timer.stop(),
    this.timer = null),
    t.pics > 1 && (this.timer = new s.A({
        func: this.updateImage.bind(this),
        interval: 1200
    }),
    this.el = e,
    this.pic = e.querySelector(".j-thumbnail"),
    this.data = t,
    null == t.currentImg && (t.currentImg = 1),
    this.timer.start(),
    this.firstSlideName = wb.helpers.getCardImgName({
        nmId: t.nmId || t.cod1S,
        viewFlags: t.viewFlags,
        idx: 1
    })),
    this
}
"""

def cdn_ranges():
    n2id = ["01"]
    prev = 0
    for i, last in enumerate(( # все числа здесь включительные! например: 143 = "01", 144 = "02"
         143,  287,  431,  719, 1007, 1061, 1115, 1169, 1313, 1601, # "01" - "10"
        1655, 1919, 2045, 2189, 2405, 2621, 2837, 3053, 3269, 3485, # "11" - "20"
        3701, 3917, 4133, 4349, 4565, 4877, 5189, 5501, 5813, 6125, # "21" - "30"
        6437, 6749, 7061, 7373,                                     # "31" - "34"
    ), 1):
        count, prev = last - prev, last
        n2id.extend((f"{i:02}",) * count)
    assert len(n2id) == 7374
    # for n in range(200, 300): print(n, n2id[n])

    def to_id(n):
        assert n >= 0
        if n <= 7373: return n2id[n]
        return "35"
    return to_id
to_id = cdn_ranges()

def id2image(n):
    id = to_id(n // 100000)
    return f"https://basket-{id}.wbbasket.ru/vol{n // 100000}/part{n // 1000}/{n}/images/c516x688/%s.webp"



asyncio.run(run_v2("https://www.wildberries.ru/catalog/igrushki/antistress", "cookies.asd", "cookies", cb_factory))



""" Распределение нагрузок:
volStaticHost(e, t=!1) {
    if (this.volStaticHostCdn) {
        const n = this.volStaticHostCdn(e, t);
        if (n)
            return n
    }
    let n;
    const r = e;
    switch (!0) {
    case r >= 0 && r <= 4:
        n = "01";
        break;
    case r >= 20 && r <= 35:
        n = "02";
        break;
    case r >= 40 && r <= 54:
        n = "03";
        break;
    case r >= 70 && r <= 113:
        n = "04";
        break;
    case r >= 114 && r <= 125:
        n = "05";
        break;
    case r >= 126 && r <= 137:
        n = "06";
        break;
    case r >= 138 && r <= 149:
        n = "07";
        break;
    default:
        n = "08"
    }
    return `static-basket-${n}.wbbasket.ru/vol${r}`
}
volHostV2(e, t=!1) {
    if (this.volHostV2Cdn) {
        const n = this.volHostV2Cdn(e, t);
        if (n)
            return n
    }
    let n;
    const r = ~~(e / 1e5);
    switch (!0) {
    case r >= 0 && r <= 143:
        n = "01";
        break;
    case r <= 287:
        n = "02";
        break;
    case r <= 431:
        n = "03";
        break;
    case r <= 719:
        n = "04";
        break;
    case r <= 1007:
        n = "05";
        break;
    case r <= 1061:
        n = "06";
        break;
    case r <= 1115:
        n = "07";
        break;
    case r <= 1169:
        n = "08";
        break;
    case r <= 1313:
        n = "09";
        break;
    case r <= 1601:
        n = "10";
        break;
    case r <= 1655:
        n = "11";
        break;
    case r <= 1919:
        n = "12";
        break;
    case r <= 2045:
        n = "13";
        break;
    case r <= 2189:
        n = "14";
        break;
    case r <= 2405:
        n = "15";
        break;
    case r <= 2621:
        n = "16";
        break;
    case r <= 2837:
        n = "17";
        break;
    case r <= 3053:
        n = "18";
        break;
    case r <= 3269:
        n = "19";
        break;
    case r <= 3485:
        n = "20";
        break;
    case r <= 3701:
        n = "21";
        break;
    case r <= 3917:
        n = "22";
        break;
    case r <= 4133:
        n = "23";
        break;
    case r <= 4349:
        n = "24";
        break;
    case r <= 4565:
        n = "25";
        break;
    case r <= 4877:
        n = "26";
        break;
    case r <= 5189:
        n = "27";
        break;
    case r <= 5501:
        n = "28";
        break;
    case r <= 5813:
        n = "29";
        break;
    case r <= 6125:
        n = "30";
        break;
    case r <= 6437:
        n = "31";
        break;
    case r <= 6749:
        n = "32";
        break;
    case r <= 7061:
        n = "33";
        break;
    case r <= 7373:
        n = "34";
        break;
    default:
        n = "35"
    }
    return `basket-${n}.wbbasket.ru/vol${r}`
}
"""
