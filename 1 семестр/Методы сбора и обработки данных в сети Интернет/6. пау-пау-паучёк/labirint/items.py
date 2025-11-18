import scrapy # pip install Scrapy

class BookItem(scrapy.Item):
    _id = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    price = scrapy.Field()
    discount_price = scrapy.Field()
    rating = scrapy.Field()
    pubhouse = scrapy.Field()
    series = scrapy.Field()
    reviews = scrapy.Field()
