from .utils import get_MongoDB_connection

from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout, DuplicateKeyError
import os

class MongoPipeline:
    def open_spider(self, spider):
        self.client = get_MongoDB_connection()
        self.db = self.client["instagram"]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        Type, data = item
        while True:
            try:
                match Type:
                    case "source":
                        copy = dict(data)
                        self.db.users.update_one({"_id": copy.pop("id")}, {"$set": copy}, upsert=True)
                    case "following":
                        copy = dict(data)
                        source = copy.pop("source")
                        self.db[f'following_{source["username"]}'].update_one({"_id": copy.pop("id")}, {"$set": copy}, upsert=True)
                    case "follower":
                        copy = dict(data)
                        source = copy.pop("source")
                        self.db[f'follower_{source["username"]}'].update_one({"_id": copy.pop("id")}, {"$set": copy}, upsert=True)
                    case "avatar":
                        path, body = data
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "wb") as f:
                            f.write(body)
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
