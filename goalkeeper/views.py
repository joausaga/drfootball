# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from goalkeeper.wiki_scrapers import WikiScraper


def index(request):
    return HttpResponse("Hello, this is the app implemented to crawl the web looking for data about football")


def to_unicode_or_bust(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def scrape(request):
    scraper = WikiScraper()
    return HttpResponse(scraper.scrape())
