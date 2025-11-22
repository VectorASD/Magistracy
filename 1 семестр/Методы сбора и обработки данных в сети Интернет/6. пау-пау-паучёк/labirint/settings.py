ITEM_PIPELINES = {
    'labirint.pipelines.MongoPipeline': 300, # приоритет... т.к. пайплайн один, смысла в нём нет ;'-}
}
SPIDER_MODULES = ['labirint.spiders'] # C:\Users\VectorASD\AppData\Local\Programs\Python\Python313\Lib\site-packages\scrapy\spiderloader.py (класс SpiderLoader) ЗДЕСЬ ВСЯ МАГИЯ ;'-}

LOG_LEVEL = 'DEBUG' # или CRITICAL, ERROR, WARNING, INFO, DEBUG
LOG_FILE  = "scrapy.log"

with open(LOG_FILE, "w"): pass
