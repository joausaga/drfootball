# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


class Player(models.Model):
    first_name = models.CharField(max_length=100, null=False)
    last_name = models.CharField(max_length=100, null=False)
    nationality = models.ForeignKey(Country)
    birth_date = models.DateField(null=True)
    teams = models.ManyToManyField(Team)
    games = models.ManyToManyField(Game)
    positions = models.ManyToManyField(Position)
    red_cards = models.IntegerField(default=0)
    #games_as_starter = models.IntegerField(default=0)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Team(models.Model):
    pass


class Coach(models.Model):
    pass


class Venue(models.Model):
    pass


class Game(models.Model):
    pass


class Tournament(models.Model):
    pass


class Goal(models.Model):
    author = models.ForeignKey(Player, on_delete=models.CASCADE)


class Position(models.Model):
    pass


class Country(models.Model):
    name = models.CharField(max_length=100, null=False)

    def __unicode__(self):
        return "%s" % self.name


class Region(models.Model):
    name = models.CharField(max_length=100, null=False)
    country = models.ForeignKey(Country)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.country.name)


class City(models.Model):
    name = models.CharField(max_length=100, null=False)
    region = models.ForeignKey(Region)

    def __unicode__(self):
        return "%s, %s, %s" % (self.name, self.region.name, self.region.country.name)
