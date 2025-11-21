import scrapy
import json
# import requests # pip install requests
from pprint import pprint, pformat
from urllib.parse import urlencode, urlparse
import os



import sys
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.append(BASE_DIR)
# print(BASE_DIR)
# print(os.getcwd())
# print(os.getcwdb().decode("utf-8")) # равнозначно os.getcwd()

from ASDsecrets import Storage



"""
storage = Storage("token.asd")
# storage.store({"token": TOKEN}, "secret", "instagram.asd")
TOKEN = storage.load("instagram.asd", "instagram token")["token"]

def test_token():
    result = requests.get(f"https://graph.instagram.com/me?fields=id,username&access_token={TOKEN}")
    if result.ok:
        print("Успешно:", result.json()) # {'id': '...', 'username': '...'}
    else: # намеренно отпилил от токена все символы, кроме первых двух: {TOKEN[:5]}
        print("Ошибка:", result.json()) # {'error': {'message': 'Failed to decrypt', 'type': 'OAuthException', 'code': 190, 'fbtrace_id': 'AtDw9mpx2lCHMawhpE7pJES'}}
    exit()

# Проблема такого подхода заключается в том, что я создал БИЗНЕС аккаунт...
# можно управлять своей страницей как угодно, но не считывать чужие :/

print(test_token())
"""



# cookies = {...}
# headers = {...}
# username = "tshn.d"

# session = requests.Session()
# for name, value in cookies.items():
#     session.cookies.set(name, value, domain=".instagram.com")
# session.headers.update(headers)

# result = session.get("https://www.instagram.com/api/v1/users/web_profile_info/", params={"username": username})
# data = result.json()
# if not result.ok or data["status"] != "ok":
#     print("Ошибка:", result.status_code, data)
#     exit()
# source = data["data"]["user"]



"""
params = {
    "count": 12,
}
for i in range(3):
    result = session.get(f'https://www.instagram.com/api/v1/friendships/{source["id"]}/following/', params=params)
    data = result.json()
    if not result.ok or data["status"] != "ok":
        print("Ошибка:", result.status_code, data)
        exit()

    for user in data["users"]:
        id        = user["id"]
        check     = user["id"] == str(user["pk"]) == user["pk_id"] == user["strong_id__"]
        username  = user["username"]
        full_name = user["full_name"]
        pic_url   = user["profile_pic_url"]
        flags     = "|".join(flag for flag in ("favorite", "private", "verified") if user["is_" + flag])
        if not flags: flags = "x"
        misc      = {name: user[name] for name in ("account_badges", "fbid_v2", "has_anonymous_profile_picture", "latest_reel_media", "profile_pic_id", "third_party_downloads_enabled")}
        print(id, check, username, full_name, pic_url, flags, misc)

    if not data["has_more"]: break
  # params["max_id"] = params.get("max_id", 0) + data["page_size"]
    params["max_id"] = data["next_max_id"] # упс, проглядел "next_max_id" ;'-}
"""

class InstagramSpider(scrapy.Spider):
    name = "instagram"
    custom_settings = {
        "USER_AGENT": "Instagram 155.0.0.37.107"
    }

    def __init__(self, usernames=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usernames = usernames.split(",") if usernames else ()

        storage = Storage("token.asd")
        tokens = storage.load("instagram.asd", "instagram token")
      # tokens["cookies"] = self.cookies; storage.store(tokens, None, "instagram.asd")
        self.cookies = tokens["cookies"]

        self.headers = {
            "User-Agent": "Instagram 155.0.0.37.107 Android (28/9; 420dpi; 1080x1920; Google; Pixel 2; pixel_2; qcom; ru_RU)",
            "Accept": "*/*",
            "Accept-Language": "ru-RU"
        }

    def request(self, url, params, callback, meta=None):
        netloc = urlparse(url).netloc
        if not netloc:
            parsed = urlparse("https://www.instagram.com" + url)
            url = f"https://{parsed.netloc}{parsed.path}"
        use_cookies = netloc.endswith(".instagram.com") or netloc == "instagram.com"
        return scrapy.Request(
            f"{url}?{urlencode(params)}" if params else url,
            cookies  = self.cookies if use_cookies else None,
            headers  = self.headers,
            callback = callback,
            meta     = meta,
        )

    def check_response(self, response):
        data = response.json()
        if response.status not in range(200, 300) or data["status"] != "ok":
            self.logger.error(f'{"~" * 77}\nURL: {response.url}\nОшибка: {response.status}\n{pformat(data)}\n{"~" * 77}')
            return
        return data

    def check_bin_response(self, response):
        body = response.body
        if response.status not in range(200, 300):
            self.logger.error(f'{"~" * 77}\nURL: {response.url}\nОшибка: {response.status}\n{body}\n{"~" * 77}')
            return
        return body



    def start_requests(self):
        for username in self.usernames:
            url = "https://www.instagram.com/api/v1/users/web_profile_info/"
            params = {"username": username}
            yield self.request(url, params, self.parse_user)

    def parse_user(self, response):
        data = self.check_response(response)
        if data is None: return

        source = data["data"]["user"]
        yield "source", source

        # подписки
        url = f"https://www.instagram.com/api/v1/friendships/{source['id']}/following/"
        params = {"count": 25}
        yield self.request(url, params, self.parse_following, {"url": url, "source": source})

        # подписчики
        url = f"https://www.instagram.com/api/v1/friendships/{source['id']}/followers/"
        params = {"count": 25, "search_surface": "follow_list_page"}
        yield self.request(url, params, self.parse_followers, {"url": url, "source": source})

    def parse_following(self, response):
        data = self.check_response(response)
        if data is None: return

        # self.logger.info(pformat(data))
        source = response.meta["source"]

        for user in data["users"]:
            flags     = "|".join(flag for flag in ("favorite", "private", "verified") if user["is_" + flag])
            if not flags: flags = "x"
            user = {
                "id":        user["id"],
                "check":     user["id"] == str(user["pk"]) == user["pk_id"] == user["strong_id__"],
                "username":  user["username"],
                "full_name": user["full_name"],
                "pic_id":    user.get("profile_pic_id", f'picture_{user["id"]}'),
                "pic_url":   user["profile_pic_url"],
                "misc":      { name: user[name]
                               for name in ("account_badges", "fbid_v2", "has_anonymous_profile_picture",
                                            "latest_reel_media", "third_party_downloads_enabled")
                             },
                "source": source,
            }
            yield self.save_image(user)
            yield "following", user

        if data["has_more"]:
          # params["max_id"] = params.get("max_id", 0) + data["page_size"]
          # params["max_id"] = data["next_max_id"] # упс, проглядел "next_max_id" ;'-}
            url = response.meta["url"]
            params = {
                "count":  25,
                "max_id": data["next_max_id"],
            }
            yield self.request(url, params, self.parse_following, {"url": url, "source": source})

    def parse_followers(self, response):
        data = self.check_response(response)
        if data is None: return

        # self.logger.info(pformat(data))
        source = response.meta["source"]

        for user in data["users"]:
            flags     = "|".join(flag for flag in ("private", "verified") if user["is_" + flag])
            if not flags: flags = "x"
            user = {
                "id":        user["id"],
                "check":     user["id"] == str(user["pk"]) == user["pk_id"] == user["strong_id__"],
                "username":  user["username"],
                "full_name": user["full_name"],
                "pic_id":    user.get("profile_pic_id", f'picture_{user["id"]}'),
                "pic_url":   user["profile_pic_url"],
                "misc":      { name: user[name]
                               for name in ("account_badges", "fbid_v2", "has_anonymous_profile_picture",
                                            "latest_reel_media", "third_party_downloads_enabled")
                             },
                "source":    source,
            }
            # "allowed_commenter_type":         "any",
            # "has_onboarded_to_text_post_app": false,
            # "interop_messaging_user_fbid":    "secret_fbid_;'-}"
            # "reel_auto_archive":              "unset"
            #   встречаются только у МОЕГО аккаунта
            yield self.save_image(user)
            yield "follower", user

        if data["has_more"]:
          # params["max_id"] = params.get("max_id", 0) + data["page_size"]
          # params["max_id"] = data["next_max_id"] # упс, проглядел "next_max_id" ;'-}
            url = response.meta["url"]
            params = {
                "count":          25,
                "search_surface": "follow_list_page",
                "max_id":         data["next_max_id"],
            }
            yield self.request(url, params, self.parse_followers, {"url": url, "source": source})

    def save_image(self, user):
        def cb(response):
            body = self.check_bin_response(response)
            if body is None: return

            # with open(path, "wb") as f:
            #     f.write(body)
            yield "avatar", (path, body) # дисантируем в pipelines.py

        path = os.path.join("avatars", user["pic_id"]) + ".jpeg"
        return self.request(user["pic_url"], None, cb)
