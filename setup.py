# Automatically created by: shub deploy

from setuptools import setup, find_packages

setup(
    name = 'project',
    version = '1.3.0',
    packages = find_packages(),
    package_data={
        'kyobobook_scraper': ['resources/*']
    },
    entry_points = {'scrapy': ['settings = kyobobook_scraper.settings']},
)
