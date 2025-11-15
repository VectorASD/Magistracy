# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from pymongo import MongoClient


class JobparserPipeline:
    def __init__(self):
        client = MongoClient('localhost', 27017)
        self.mongo_base = client.vacancies1507


    def process_item(self, item, spider):
        # item['salary'] = self.process_salary(item['salary'])

        collection = self.mongo_base[spider.name]
        collection.insert_one(item)
        return item

    def process_salary(self, salary):
        min = 0
        max = 0
        cur = ''
        return min, max, cur
