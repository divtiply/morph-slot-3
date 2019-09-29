# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class KyobobookScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    isbn_13 = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    sell_price = scrapy.Field()
    original_price = scrapy.Field()
