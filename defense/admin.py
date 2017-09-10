# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from models import Source, Country, Region, City, Stadium, Player, Coach, \
                   Referee, Team, PlayerTeam, CoachTeam, StadiumTeam, \
                   Tournament, TournamentTeam, TournamentPlayer, Game, \
                   GameTeam, GamePlayer, GameReferee, Goal, Card
from django.contrib import admin
from goalkeeper import parser_rsssf
from goalkeeper.wiki_scrapers import ParaguayanChampionshipResultsScraper, \
                                     ParaguayanTournamentScraper
import itertools, re, utils


num_pattern = re.compile('[^0-9]')


def disambiguate_objs_by_name(objs, ref_name):
    similarity = []
    for obj in objs:
        nor_name = utils.normalize_text(obj.name)
        names = itertools.izip_longest(nor_name, ref_name)
        similarity.append(len([c1 for c1, c2 in names if c1 == c2]))
    idx_max_sim = similarity.index(max(similarity))
    return objs[idx_max_sim]


def create_new_team(name, stadium, wikipage=None):
    new_team = Team(name=name, city=stadium.city, stadium=stadium,
                    wikipage=wikipage)
    new_team.save()
    return new_team


def create_new_stadium(name, city, capacity, wikipage=None):
    new_stadium = Stadium(name=name, city=city, capacity=capacity,
                          wikipage=wikipage)
    new_stadium.save()
    return new_stadium


def create_new_city(name, country, wikipage=None):
    new_city = City(name=name, country=country, wikipage=wikipage)
    new_city.save()
    return new_city


class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'queried')


class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'start_date', 'end_date', 'champion', 'runnerup')
    actions = ['collect_extra_info', 'collect_results']

    def champion(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_position == 1:
                return tournament_team.team.name
        return ''

    def runnerup(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_position == 2:
                return tournament_team.team.name
        return ''

    def __get_or_create_team(self, team):
        team_name = utils.normalize_text(team['equipo'])
        team_objs = Team.objects.filter(name__icontains=team_name)
        if len(team_objs) == 1:
            return team_objs[0]
        elif len(team_objs) > 1:
            return disambiguate_objs_by_name(team_objs, team_name)
        elif len(team_objs) == 0:
            # the team doesn't exist yet
            stadium_name = utils.normalize_text(team['estadio'])
            stadium_objs = Stadium.objects.filter(name__icontains=stadium_name)
            if len(stadium_objs) == 0:
                # the stadium doesn't exist yet
                city_name = utils.normalize_text(team['ciudad'])
                capacity = int(num_pattern.sub('', team['capacidad'])) if 'capacidad' in team.keys() else -1
                city_objs = City.objects.filter(name__icontains=city_name)
                if len(city_objs) == 0:
                    # the city doesn't exist, the default country for
                    # all cities will be paraguay
                    country = Country(name__icontains='paraguay')
                    if 'wikipage' in team['city'].keys():
                        city = create_new_city(city_name, country, team['city']['wikipage'])
                    else:
                        city = create_new_city(city_name, country)
                elif len(city_objs) == 1:
                    city = city_objs[0]
                elif len(city_objs) > 1:
                    city = disambiguate_objs_by_name(city_objs, city_name)
                else:
                    raise Exception('Error!, Dont understand the number of cities')
                if 'wikipage' in team['stadium'].keys():
                    stadium = create_new_stadium(stadium_name, city, capacity, team['stadium']['wikipage'])
                else:
                    stadium = create_new_stadium(stadium_name, city, capacity)
            elif len(stadium_objs) == 1:
                stadium = stadium_objs[0]
            elif len(stadium_objs) > 1:
                stadium = disambiguate_objs_by_name(stadium_objs, stadium_name)
            else:
                raise Exception('Error!, Dont understand the number of stadiums')
        else:
            raise Exception('Error!, Dont understand the number of teams')
        if 'wikipage' in team.keys():
            new_team = create_new_team(team_name, stadium, team['wikipage'])
        else:
            new_team = create_new_team(team_name, stadium)
        return new_team

    def collect_extra_info(self, request, queryset):
        for obj in queryset:
            py_ch_scrapper = ParaguayanTournamentScraper(obj.source.all()[0].url)
            tournament = {
                'name': obj.name,
                'year': obj.year,
                'additional_info': obj.additional_info
            }
            print(tournament)
            tournament_info = py_ch_scrapper.collect_tournament_info(tournament)
            print(tournament_info)
            if 'teams_info' in tournament_info.keys():
                for team in tournament_info['teams']:
                    # add teams to tournament
                    team = self.__get_or_create_team(team)
                    obj.teams.add(team)
    collect_extra_info.short_description = "Collect Extra Information"

    def collect_results(self, request, queryset):
        pass
    collect_results.short_description = "Collect Tournament Results"


class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('team', 'tournament', 'final_position')


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'birth_date', 'local_championships',
                    'international_championships')
    ordering = ('name', 'birth_date', 'local_championships', 'international_championships')


class GameAdmin(admin.ModelAdmin):
    list_display = ('game_date', 'game_time', 'tournament', 'round', 'game_stadium',
                    'home', 'away', 'score')
    ordering = ('tournament', 'round')

    def game_date(self, obj):
        return obj.datetime.date()

    def game_time(self, obj):
        if obj.datetime.hour == 0 and \
           obj.datetime.minute == 0:
            return 'Unknown'
        else:
            return obj.datetime.time()

    def game_stadium(self, obj):
        if obj.stadium is None:
            return 'Unknown'
        else:
            return obj.stadium

    def home(self, obj):
        game_teams = obj.gameteam_set.all()
        if game_teams[0].home:
            return game_teams[0].team.name
        else:
            return game_teams[1].team.name

    def away(self, obj):
        game_teams = obj.gameteam_set.all()
        if game_teams[0].home:
            return game_teams[1].team.name
        else:
            return game_teams[0].team.name

    def score(self, obj):
        game_teams = obj.gameteam_set.all()
        if game_teams[0].home:
            home_idx = 0
            away_idx = 1
        else:
            home_idx = 1
            away_idx = 0
        ret = '%s - %s' % (game_teams[home_idx].goals, game_teams[away_idx].goals)
        return ret


class GameTeamAdmin(admin.ModelAdmin):
    list_display = ('game', 'team', 'goals')


admin.site.register(Source, SourceAdmin)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(City)
admin.site.register(Stadium)
admin.site.register(Player)
admin.site.register(Coach)
admin.site.register(Referee)
admin.site.register(Team, TeamAdmin)
admin.site.register(PlayerTeam)
admin.site.register(CoachTeam)
admin.site.register(StadiumTeam)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentTeam, TournamentTeamAdmin)
admin.site.register(TournamentPlayer)
admin.site.register(Game, GameAdmin)
admin.site.register(GameTeam, GameTeamAdmin)
admin.site.register(GamePlayer)
admin.site.register(GameReferee)
admin.site.register(Goal)
admin.site.register(Card)
