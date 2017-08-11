__author__ = 'jorgesaldivar'

from django.conf.urls import url

from . import views

urlpatterns = [
    # ex: /goalkeeper
    url(r'^$', views.index, name='index'),
    # ex: /goalkeeper/scrape
    url(r'^scrape$', views.scrape, name='scrape'),
]
