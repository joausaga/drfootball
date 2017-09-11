# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Define constants
LEG_TYPES = (
    ('right', 'Right'),
    ('left', 'Left'),
    ('both', 'Both'),
)

GOAL_TYPES = (
    ('penalty', 'Penalty'),
    ('freekick', 'Freekick'),
    ('head', 'Head'),
    ('right', 'Right'),
    ('left', 'Left'),
    ('owngoal', 'Own Goal'),
)

CARD_TYPES = (
    ('direct_red', 'Direct Red'),
    ('red', 'Red'),
    ('yellow', 'Yellow'),
)

STADIUM_OWNER_TYPES = (
    ('public', 'Public'),
    ('private', 'Private'),
)

POSITIONS = (
    ('goalkeeper', 'Goalkeeper'),
    ('defense', 'Defense'),
    ('midfielder', 'Midfielder'),
    ('forward', 'Forward'),
)

LEAGUE = (
    ('first', 'First'),
    ('second', 'Second'),
    ('third', 'Third'),
    ('fourth', 'Fourth'),
)

SYSTEM = (
    ('todos', 'Todos contra todos'),
    ('liguilla', 'Liguilla'),
    ('final', 'Final'),
)

REF_ROLES = (
    ('main', 'Main'),
    ('lineman', 'Lineman'),
    ('fourth', 'Fourth'),
    ('other', 'Other'),
)

FINAL_STATUS = (
    ('champion', 'Champion'),
    ('runnerup', 'Runnerup'),
    ('int_cup', 'International Cup'),
    ('relegation', 'Relegation'),
    ('subrelegation', 'Sub Relegation'),  # what in south-america is known as 'promocion'
    ('other', 'Other'),
)

TACTICS = (
    ('442', '4-4-2'),
    ('433', '4-3-3'),
    ('352', '4-5-2'),
    ('532', '5-3-2'),
    ('523', '5-2-3'),
    ('343', '3-4-3'),
    ('532', '5-3-2'),
    ('2143', '2-1-4-3'),
    ('3142', '3-1-4-2'),
    ('3223', '3-2-2-3'),
    ('3232', '3-2-3-2'),
    ('4411', '4-4-1-1'),
    ('4141', '4-1-4-1'),
    ('other', 'Other'),
)

# Create your models here.


class Source(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    queried = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s: %s" % (self.name, self.url)


class Country(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return "%s" % self.name


class Region(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.country.name)


class City(models.Model):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, blank=True, null=True)
    country = models.ForeignKey(Country, default=1)  # 1 == Paraguay
    wikipage = models.URLField(blank=True, null=True)

    def __unicode__(self):
        if self.region:
            return "%s, %s" % (self.name, self.region.country.name)
        else:
            return "%s, %s" % (self.name, self.country.name)


class Stadium(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City)
    capacity = models.IntegerField(null=True, blank=True)
    picture = models.ImageField(null=True, blank=True)
    owner_type = models.CharField(max_length=50, null=True, blank=True,
                                  choices=STADIUM_OWNER_TYPES)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    wikipage = models.URLField(blank=True, null=True)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.city)


class Player(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.ForeignKey(Country)
    birth_date = models.DateField(null=True, blank=True)
    picture = models.ImageField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    positions = models.CharField(max_length=50, null=True, blank=True,
                                 choices=POSITIONS)
    leg = models.CharField(max_length=50, null=True, blank=True,
                           choices=LEG_TYPES)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Coach(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.ForeignKey(Country)
    birth_date = models.DateField(null=True, blank=True)
    picture = models.ImageField(null=True, blank=True)
    championships = models.IntegerField(default=0)
    runnerups = models.IntegerField(default=0)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Referee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.ForeignKey(Country)
    birth_date = models.DateField(null=True, blank=True)
    picture = models.ImageField(null=True, blank=True)

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Team(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City)
    stadium = models.ManyToManyField(Stadium, through='StadiumTeam')
    badge = models.ImageField(null=True, blank=True)
    foundation = models.DateField(null=True, blank=True)
    local_championships = models.IntegerField(default=0)
    local_runnerups = models.IntegerField(default=0)
    international_championships = models.IntegerField(default=0)
    international_runnerups = models.IntegerField(default=0)
    players = models.ManyToManyField(Player, through='PlayerTeam')
    coaches = models.ManyToManyField(Coach, through='CoachTeam')
    total_games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    wikipage = models.URLField(blank=True, null=True)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.city)


class PlayerTeam(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    data_joined = models.DateField()
    transfer_us_dollar = models.FloatField(null=True, blank=True)
    championships = models.IntegerField(default=0)
    runnerups = models.IntegerField(default=0)
    games = models.IntegerField(default=0)
    games_as_started = models.IntegerField(default=0)
    games_as_substituted = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    cards = models.IntegerField(default=0)
    source = models.ManyToManyField(Source)


class CoachTeam(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    date_joined = models.DateField()
    transfer_us_dollar = models.FloatField(null=True, blank=True)
    championships = models.IntegerField(default=0)
    runnerups = models.IntegerField(default=0)
    games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    source = models.ManyToManyField(Source)


class StadiumTeam(models.Model):
    stadium = models.ForeignKey(Stadium, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    from_date = models.DateField(null=True, blank=True)
    source = models.ForeignKey(Source, default='')


class Tournament(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    league = models.CharField(max_length=50, null=True, blank=True,
                              choices=LEAGUE)
    year = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    edition = models.IntegerField(null=True, blank=True)
    points_for_victory = models.IntegerField(default=3)
    rounds = models.IntegerField(null=True, blank=True)
    number_of_teams = models.IntegerField(default=12)
    system = models.CharField(max_length=50, null=True, blank=True,
                              choices=SYSTEM)
    teams = models.ManyToManyField(Team, through='TournamentTeam')
    scorers = models.ManyToManyField(Player, through='TournamentPlayer')
    champion_of_season = models.BooleanField(default=True)
    source = models.ManyToManyField(Source)
    result_source = models.ManyToManyField(Source, related_name='results_source')
    # for internal usage only
    season_champion = models.BooleanField(default=False)
    record_problem = models.CharField(max_length=50, null=True, blank=True)
    start_string = models.CharField(max_length=50, null=True, blank=True)
    end_string = models.CharField(max_length=50, null=True, blank=True)
    additional_info = models.CharField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.country)


class TournamentPlayer(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    goals = models.IntegerField(default=0)
    cards = models.IntegerField(default=0)
    minutes = models.IntegerField(default=0)
    as_starter = models.IntegerField(default=0)
    source = models.ManyToManyField(Source)


class TournamentTeam(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    cards = models.IntegerField(default=0)
    final_position = models.IntegerField(default=0)
    source = models.ForeignKey(Source, default='')


class TournamentStatus(models.Model):
    name = models.CharField(max_length=100)


class SeasonTeamFinalStatus(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    season = models.IntegerField(default=0)
    status = models.ForeignKey(TournamentStatus, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)


class Game(models.Model):
    datetime = models.DateTimeField(null=True, blank=True)
    round = models.IntegerField()
    stadium = models.ForeignKey(Stadium, on_delete=models.CASCADE, null=True, blank=True)
    picture = models.ImageField(null=True, blank=True)
    teams = models.ManyToManyField(Team, through='GameTeam')
    referees = models.ManyToManyField(Referee, through='GameReferee')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    income = models.IntegerField(null=True, blank=True)
    audience = models.IntegerField(null=True, blank=True)
    players = models.ManyToManyField(Player, through='GamePlayer')
    source = models.ManyToManyField(Source)

    def __unicode__(self):
        return "%s - %s, round: %s" % (self.datetime.date(), self.tournament.name, self.round)


class GameTeam(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    home = models.BooleanField(default=True)
    goals = models.IntegerField(default=0)
    tactic = models.CharField(max_length=50, choices=TACTICS, null=True, blank=True)


class GamePlayer(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    starter = models.BooleanField(default=True)
    minutes = models.FloatField(null=True, blank=True)
    goals = models.IntegerField(default=0)
    cards = models.IntegerField(default=0)
    source = models.ManyToManyField(Source)


class GameReferee(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    referee = models.ForeignKey(Referee, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='main', choices=REF_ROLES)
    source = models.ManyToManyField(Source)


class TournamentReferee(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    referee = models.ForeignKey(Referee, on_delete=models.CASCADE)
    games = models.IntegerField(default=0)
    yellow_cards = models.IntegerField(default=0)
    red_cards = models.IntegerField(default=0)


class Goal(models.Model):
    author = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='goals')
    type = models.CharField(max_length=50, null=True, choices=GOAL_TYPES)
    minute = models.IntegerField(null=True, blank=True)
    own = models.BooleanField(default=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    assistant = models.ForeignKey(Player, on_delete=models.CASCADE, null=True,
                                  related_name='assistances')
    source = models.ManyToManyField(Source)

    def __unicode__(self):
        return "%s, %s, %s" % (self.author, self.type, self.minute)


class Card(models.Model):
    author = models.ForeignKey(Player, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, default='red', choices=CARD_TYPES)
    minute = models.IntegerField(null=True, blank=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    source = models.ManyToManyField(Source)

    def __unicode__(self):
        return "%s, %s, %s" % (self.author, self.type, self.minute)