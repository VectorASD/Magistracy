ITEM_PIPELINES = {
    'instagram.pipelines.MongoPipeline': 300, # приоритет... т.к. пайплайн один, смысла в нём нет ;'-}
}
SPIDER_MODULES = ['instagram.spiders'] # C:\Users\VectorASD\AppData\Local\Programs\Python\Python313\Lib\site-packages\scrapy\spiderloader.py (класс SpiderLoader) ЗДЕСЬ ВСЯ МАГИЯ ;'-}

LOG_LEVEL = 'INFO' # или CRITICAL, ERROR, WARNING, INFO, DEBUG
LOG_FILE  = "scrapy.log"

with open(LOG_FILE, "w"): pass
