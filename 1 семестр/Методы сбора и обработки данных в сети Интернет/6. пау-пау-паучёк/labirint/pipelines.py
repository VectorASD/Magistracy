from .utils import get_MongoDB_connection

from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout, DuplicateKeyError

class MongoPipeline:
    def open_spider(self, spider):
        self.client = get_MongoDB_connection()
        self.db = self.client["books_db"]
        self.collection = self.db["books"]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        doc = dict(item)
        while True:
            try:
                self.collection.insert_one(doc)
                break
            except DuplicateKeyError:
                break
            except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
                spider.logger.warning(f"Mongo insert failed: {e}. Retrying in 0.1s...")
                time.sleep(0.1)
            except Exception as e:
                spider.logger.error(f"Unexpected Mongo error: {e}")
                # если ошибка не связана с сетью, лучше не зацикливаться
                raise
        return item
