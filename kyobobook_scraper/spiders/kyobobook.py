# -*- coding: utf-8 -*-
import pkgutil
from datetime import datetime
import json
import scrapy
import w3lib


class KyoboBookSpider(scrapy.Spider):
    name = 'kyobobook'
    allowed_domains = ['www.kyobobook.co.kr', 'rb-rec-api-apne1.recobell.io']
    base_url = 'http://www.kyobobook.co.kr'
    start_urls = ['http://www.kyobobook.co.kr/indexKor.laf?mallGb=KOR']
    mode = None  # fast/deep/isbn

    def start_requests(self):
        if self.mode == 'isbn':
            isbnlist = pkgutil.get_data('kyobobook_scraper', 'resources/isbnlist.txt').decode()
            for isbn in isbnlist.splitlines():
                yield self.item_request(isbn)
        else:
            super(KyoboBookSpider, self).start_requests()

    def parse(self, r):
        for a in r.xpath('.//*[@class="nav_category"]//li[not(ul)]/a'):
            yield r.follow(a, self.drill_down)

    def drill_down(self, r):
        # var subcategories = $('.path_bar .location_zone:has(em) a')
        subcategories = r.css('.path_bar .location_zone').xpath('self::*[.//em]//a') 
        for subcategory in subcategories:
            yield r.follow(subcategory, self.drill_down)
        # There are two types of category pages: "real" and "virtual"
        # Virutual ones not contain "전체보기" ("View all") tab and their
        # pagination links are like "javascript:_go_targetPage('1')"
        # Real pagination links are like "javascript:golist2(0);"
        # Only real ones are scraped.
        if not subcategories:
            # FIXME: next test wrong if there is only one page in real category
            category_is_real = r.css('.list_paging .btn_next[href*=golist2]')
            if category_is_real:
                url = w3lib.url.add_or_replace_parameter(r.url, 'vPviewCount', 200)  # items per page
                yield r.follow(url, self.parse_list)

    def parse_list(self, r):
        timestamp = datetime.utcnow()
        next_page_link = r.css('.list_paging .btn_next')
        if next_page_link:
            start = next_page_link.xpath('@href').re_first(r"golist2\(([^)]+)\)")
            next_page_url = w3lib.url.add_or_replace_parameter(r.url, 'vPstartno', start)
            yield r.follow(next_page_url, self.parse)
        # for item_link in r.css('#container .prd_list_area .id_detailli .title a'):
        for e in r.css('#container .prd_list_area .id_detailli'):
            mall_gb, link_class, barcode = e.css('.title a::attr(href)').re(r"'([^']+)'")
            if self.mode == 'deep':
                yield self.item_request(barcode)
            else: # if mode == 'fast':
                i = {}
                i['timestamp'] = timestamp
                i['mall_gb'] = mall_gb
                i['link_class'] = link_class
                i['isbn_13'] = barcode
                # title consists of parts: [FRONT] <strong>TITLE</strong> [BACK] [INFO]
                # see 9788997937042, 9788913012228
                i['title'] = ''.join(e.css('.title a').xpath('node()').getall()).strip()
                i['pub_info'] = e.css('.pub_info').get()
                i['sell_price'] = e.css('.sell_price::text').get().replace(',', '')
                yield i

    def item_request(self, barcode, **kwargs):
        url = self.base_url + '/product/detailViewKor.laf?barcode=' + barcode
        return scrapy.Request(url, self.parse_item, **kwargs)

    def parse_item(self, r):
        timestamp = datetime.utcnow()
        i = {}
        i['timestamp'] = timestamp
        f = r.css('#container [name=proForm]')
        # subbooknm: javascript:goDetailProduct('KOR','421917','9791161721422')
        # http://www.kyobobook.co.kr/product/detailViewKor.laf?ejkGb=KOR&mallGb=KOR&barcode=9788994757056
        # 초등학생이 가장 궁금해하는 신비한 우주 이야기 30
        # 초등학생이 가장 궁금해하는 신비한 우주 이야기 30
        # 신비한 우주 이야기 30(초등학생이 가장 궁금해하는)
        i['title_front'] = safe_strip(f.css('.title .front > strong::text').get())
        i['title'] = safe_strip(f.css('.title > strong::text').get())
        i['title_back'] = safe_strip(f.css('.title .back > strong::text').get())
        i['info'] = safe_strip(f.css('.info::text').get())
        # Shitty author string examples:
        # (multiple published date, multiple authors)
        # http://www.kyobobook.co.kr/product/detailViewEng.laf?mallGb=ENG&ejkGb=ENG&barcode=9780439673631&orderClick=JAD#review
        # http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&linkClass=2301&barcode=9791160802948
        i['author_html'] = f.css('.author').get().translate({ord(c): None for c in '\r\n\t'})
        i['author'] = ';'.join(
            t.get().strip() for t in f.css('.author .detail_author::text')
        ).translate({ord(c): None for c in '\r\n\t'})
        i['translator'] = ';'.join(t.get().strip() for t in f.css('.author .detail_translator::text'))
        i['publisher'] = f.css('.author .name[title="출판사"] a::text').get()
        i['published_date'] = (
            f.css('.author .date[title="출간일"]::text').get()
            .translate({ord(c): None for c in '\r\n\t'})
            .replace('년 ', '.')
            .replace('월 ', '.')
            .replace('일', '')
            .replace(' 출간', '')
        )
        i['sell_price'] = f.css('.sell_price strong::text').get().replace(',', '')
        i['original_price'] = f.css('.org_price::text').re_first(r'[\d,.]+').replace(',', '')
        i['arrived_date'] = f.css('#basic_sendinfo_area em::text').get()
        i['klover_rating'] = f.css('.review .review_klover em::text').get()
        i['klover_vote_count'] = ''.join(
            f.css('.review .review_klover .popup_load::text').getall()).strip().strip('()')
        i['rating'] = f.css('.review a[href="#review"] img::attr(alt)').re_first(r'\d+')
        i['review_count'] = f.css('.review a[href="#review"]::text').re_first(r'\d+')
        i['isbn_13'] = r.css('span[title="ISBN-13"]::text').get()
        i['isbn_10'] = r.css('span[title="ISBN-10"]::text').get()
        i['page_count'] = r.css('th[scope=row]:contains("쪽수") + td::text').re_first(r'\d+')
        i['size'] = r.css('th[scope=row]:contains("크기") + td::text').get()#.strip()
        i['original_title'] = r.css('th[scope=row]:contains("이 책의 원서/번역서") + td::text').get()#.strip()
        i['breadcrumbs'] = ';'.join(
            ' '.join(t.get().strip() for t in li.css('a::text'))
            for li in r.css('h3.title_detail_category + ul.list_detail_category li'))
        i['hashtags'] = ';'.join(t.rstrip('# ') for t in r.css('.tag_list a em::text').getall())
        yield i
        # yield self.keywords_request(i['isbn13'], meta={'item': i})

    def keywords_request(self, barcode, **kwargs):
        # To see keywords look for recobel.io requests with adblock disabled
        url = 'http://rb-rec-api-apne1.recobell.io/rec/kyobo002?key=' + barcode
        return scrapy.Request(url, self.parse_keywords, **kwargs)

    def parse_keywords(self, r):
        i = r.meta['item']
        j = json.loads(r.text)
        if j['groupedResults']:
            kws = next(iter(j['groupedResults'].values()))
            keywords = ';'.join(x['itemId'] for x in kws)
        else:
            keywords = ''
        i['keywords'] = keywords
        yield i


def safe_strip(text):
    return text.strip() if text else text
