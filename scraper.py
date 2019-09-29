# -*- coding: utf-8 -*-

# Script executed by morph.io to run the scraper
# https://morph.io/documentation
# https://docs.scrapy.org/en/latest/topics/practices.html#run-from-script

import os
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from dotenv import load_dotenv, find_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


morph_dotenv = os.getenv('MORPH_DOTENV')
if morph_dotenv:
    load_dotenv(stream=StringIO(morph_dotenv))
load_dotenv(find_dotenv())

settings = get_project_settings()
process = CrawlerProcess(settings)
spider_name = os.getenv('MORPH_SPIDER_NAME')
spider_args = os.getenv('MORPH_SPIDER_ARGS')
#process.crawl(spider_name)
process.crawl('kyobobook', mode='isbn')
process.start()
