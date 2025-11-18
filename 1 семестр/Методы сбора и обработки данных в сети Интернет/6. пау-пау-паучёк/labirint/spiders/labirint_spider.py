import scrapy
from ..items import BookItem

"""
<div class="swiper-slide card-column card-column_gutter col-xs-3 col-sm-2 swiper-slide-active">
    <div class="product need-watch watched gtm-watched" data-index-tool="13" data-type-tool="sh" data-product-id="918437" data-name="Сказки" data-metkascreenshot="1" data-dir="books" data-incompare="0" data-inputorder="" data-inbasket="" data-sgenre="-1" data-sgenre-name="книга" data-maingenre="2525" data-maingenre-name="Классическая отечественная проза" data-price="2397" data-first-genre="1852" data-first-genre-name="Художественная литература" data-position="1" data-discount-price="1199" data-available-status="1" data-pubhouse="Галерея классики" data-series="Слово и образ" data-object-type="product" data-action-name="Калейдоскоп чтения" data-middle-genres="2787" data-is-ebook="0" data-is-news-id="" data-best-portal="1">
        <div class="product-cover">
            <div class="relative product-cover__relative">
                <div class="product-cover__cover-wrapper">
                    <a class="cover genres-cover" href="/books/918437/" title="Михаил Салтыков-Щедрин - Сказки"> <img src="https://imo10.labirint.ru/books/918437/cover.jpg/363-0" class="book-img-cover entered loaded" data-src="https://imo10.labirint.ru/books/918437/cover.jpg/363-0" alt="Михаил Салтыков-Щедрин - Сказки обложка книги" title="Михаил Салтыков-Щедрин - Сказки" data-ll-status="loaded" style="opacity: 1; transition: opacity 0.2s;"> </a>
                    <!--noindex--><span class="product-hint" style="display: block;">
                <a href="/reviews/goods/918437/" class="js-analytics-click-product-hint" data-event-type="203" data-event-label="reviewsCount" data-event-content="4">
            <span>4</span> рец. </a>
                    <br>
                    <a href="/books/918437/#galery" class="js-analytics-click-product-hint" data-event-type="204" data-event-label="photosCount" data-event-content="45"> <span>45</span> фото </a> <span class="tip"></span> </span>
                    <!--/noindex-->
                    <a class="card-label card-label_marker card-label_color-marker" href="/top/zavodnoy-noyabr/"> <span class="card-label__text">Акция с подарком</span> </a>
                </div>
                <div class="price-label">
                    <div class="product-pricing">
                        <div class="price"> <span class="price-val" title="–50% фиксированная">
            <span>1 199</span> ₽ </span> <span class="price-old"><span class="price-gray">2 397</span></span>
                        </div>
                    </div>
                    <a class="card-label_profit card-label_container-timer" href="/top/kaleydoskop-chteniya/" rel="nofollow" title="–50% фиксированная">
                        <div class="card-label card-label_turned-timer card-label_color-big"> <span class="card-label__text card-label__text_turned">–50<span class="action-label__space">&nbsp;</span>%</span>
                        </div> <span class="card-label_timer-right">Ещё 1 день</span> </a>
                </div>
            </div>
            <a class="product-title-link" href="/books/918437/" title="Михаил Салтыков-Щедрин - Сказки">
                <span class="product-title">Сказки</span>
            </a>
        </div>
        <div class="product-author"> <a href="/authors/19556/" title="Салтыков-Щедрин Михаил Евграфович"><span>Салтыков-Щедрин Михаил Евграфович</span></a>
            <div class="fader"></div>
        </div>
        <div class="product-pubhouse"> <a class="product-pubhouse__pubhouse" href="/pubhouse/5293/" title="Галерея классики"><span>Галерея классики</span></a><span>: </span>
            <a class="product-pubhouse__series" href="/series/58207/" title="Слово и образ"> <span>Слово и образ</span> </a>
            <div class="fader"></div>
        </div>
        <div class="product-buy-area">
            <div class="product-buy-margin">
                <div class="product-buy buy-avaliable fleft"> <a data-idtov="918437" data-position="1" class="btn buy-link btn-primary" id="buy918437" href="#" onclick="shopingnew(918437, 0, 0); return false;" data-carttext="">
        В КОРЗИНУ        </a> </div>
                <div class="fleft product-icons-outer">
                    <div class="product-icons">
                        <div class="product-icons-inner"> <a class="icon-fave  track-tooltip js-open-deferred-block " data-id_book="918437" data-deferred="0" data-id_catalog="" data-tooltip_title="Отложить" data-hasqtip="0"><span class="header-sprite"></span></a> <a class="icon-compare track-tooltip js-open-actions-block" data-id_book="918437" data-incompare="0" data-rang_sort="3" data-already_have="0" data-id_author="19556" data-is_subscribed_novelties_author="0" data-url="http://www.labirint.ru/books/918437/?ref_contact=" data-short="«Сказки» в Лабиринте" data-title="Сказки в Лабиринт.ру. 2 397 р." data-image="https://imo10.labirint.ru/books/918437/cover.jpg/220-0" rel="nofollow" data-tooltip_title="Еще действия" data-hasqtip="1"><span class="header-sprite"></span></a>
                            <div class="cleaner0"></div>
                        </div>
                    </div>
                </div>
                <div class="fleft product-already-buy hidden js-block-already-have-918437"> <span class="btn-already-buy">УЖЕ ПОКУПАЛИ</span> </div>
                <div class="cleaner0"></div>
            </div>
        </div>
    </div>
</div>
"""



def safe_int(value):
    try:    return int(value)
    except: return None

class LabirintSpider(scrapy.Spider):
    name = "labirint" # отсюда и берётся "scrapy crawl labirint"
    allowed_domains = ["labirint.ru"]
    start_urls = ["https://www.labirint.ru/books/"]

    def parse(self, response):
        for book in response.css("div.product"):
            item = BookItem()
            item["_id"]            = book.attrib.get("data-product-id")
            item["url"]            = response.urljoin(book.css("a.product-title-link::attr(href)").get())
            item["title"]          = book.css("span.product-title::text").get()
            item["authors"]        = book.css("div.product-author a span::text").getall()
            item["price"]          = safe_int(book.attrib.get("data-price"))
            item["discount_price"] = safe_int(book.attrib.get("data-discount-price"))
            item["pubhouse"]       = book.attrib.get("data-pubhouse")
            item["series"]         = book.attrib.get("data-series")
            item["reviews"]        = safe_int(book.css("a[data-event-label='reviewsCount'] span::text").get())
            yield item

        # пагинация
        # <div class="pagination-next">
	    #     <a class="pagination-next__text" href="?page=2" data-tonavi-offset="120" title="Следующая">Следующая</a>
        # </div
        # <div class="pagination-next"> (последняя 17-ая страничка ;'-})
		# 	<span class="pagination-next__text disabled">Следующая</span>
        # </div>
        next_page = response.css("div.pagination-next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
