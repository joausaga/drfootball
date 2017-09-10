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
import itertools
import re
import utils


num_pattern = re.compile('[^0-9]')
DEF_COUNTRY = 'paraguay'


def disambiguate_objs_by_name(objs, ref_name):
    similarity = []
    for obj in objs:
        nor_name = utils.normalize_text(obj.name)
        names = itertools.izip_longest(nor_name, ref_name)
        similarity.append(len([c1 for c1, c2 in names if c1 == c2]))
    idx_max_sim = similarity.index(max(similarity))
    return objs[idx_max_sim]


def create_new_team(team_dict, stadium_obj):
    team_name = utils.format_text_to_save_db(team_dict['name'])
    if 'wikipage' in team_dict.keys():
        return Team.objects.create(name=team_name, city=stadium_obj.city,
                                       wikipage=team_dict['wikipage'])
    else:
        return Team.objects.create(name=team_name, city=stadium_obj.city)


def create_new_stadium(stadium_dict, city):
    stadium_name = utils.format_text_to_save_db(stadium_dict['name'])
    if 'capacity' in stadium_dict.keys():
        capacity = int(num_pattern.sub('', stadium_dict['capacity']))
    else:
        capacity = -1
    if 'wikipage' in stadium_dict.keys():
        return Stadium.objects.create(name=stadium_name, city=city, capacity=capacity,
                                      wikipage=stadium_dict['wikipage'])
    else:
        return Stadium.objects.create(name=stadium_name, city=city, capacity=capacity)


def create_new_city(city_dict, country):
    city_name = utils.format_text_to_save_db(city_dict['name'])
    if 'wikipage' in city_dict.keys():
        return City.objects.create(name=city_name, country=country, wikipage=city_dict['wikipage'])
    else:
        return City.objects.create(name=city_name, country=country)


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

    def __get_or_create_city(self, city_dict):
        city_name = utils.normalize_text(city_dict['name'])
        city_objs = City.objects.filter(name__icontains=city_name)
        if len(city_objs) == 0:
            # the city doesn't exist, the default country for
            # all cities will be paraguay
            country = Country.objects.get(name__iexact=DEF_COUNTRY)
            city = create_new_city(city_dict, country)
        elif len(city_objs) == 1:
            city = city_objs[0]
        elif len(city_objs) > 1:
            city = disambiguate_objs_by_name(city_objs, city_name)
        else:
            raise Exception('Error!, Dont understand the number of cities')
        return city

    # TODO: if the stadium exists already see what can be updated (e.g., capacity)
    def __get_or_create_stadium(self, stadium_dict, city_dict):
        stadium_name = utils.normalize_text(stadium_dict['name'])
        stadium_objs = Stadium.objects.filter(name__icontains=stadium_name)
        city = self.__get_or_create_city(city_dict)
        if len(stadium_objs) == 0:
            # the stadium doesn't exist yet
            stadium = create_new_stadium(stadium_dict, city)
        elif len(stadium_objs) == 1:
            stadium = stadium_objs[0]
        elif len(stadium_objs) > 1:
            stadium = disambiguate_objs_by_name(stadium_objs, stadium_name)
        else:
            raise Exception('Error!, Dont understand the number of stadiums')
        return stadium

    # TODO: if the team exists already see what can be updated
    def __get_or_create_team(self, team, source):
        team_name = utils.normalize_text(team['name'])
        team_objs = Team.objects.filter(name__icontains=team_name)
        stadium = self.__get_or_create_stadium(team['stadium'], team['city'])
        if len(team_objs) == 1:
            team = team_objs[0]
        elif len(team_objs) > 1:
            team = disambiguate_objs_by_name(team_objs, team_name)
        elif len(team_objs) == 0:
            # the team doesn't exist yet
            team = create_new_team(team, stadium)
        else:
            raise Exception('Error!, Dont understand the number of teams')
        # associate the team with its stadium in case the association
        # doesn't exists
        if not team.stadium.all():
            StadiumTeam.objects.create(stadium=stadium, team=team, source=source)
        return team

    def collect_extra_info(self, request, queryset):
        for obj in queryset:
            tournament_obj = obj
            source_obj = tournament_obj.source.all()[0]
            py_ch_scrapper = ParaguayanTournamentScraper(source_obj.url)
            tournament_dict = {
                'name': obj.name,
                'year': obj.year,
                'additional_info': obj.additional_info
            }
            tournament_info = py_ch_scrapper.collect_tournament_info(tournament_dict)
            information_collected = [option.strip() for option in obj.additional_info.split(';')]
            if 'teams info' in information_collected:
                for team in tournament_info['teams']:
                    # add teams to tournament
                    team_obj = self.__get_or_create_team(team, source_obj)
                    TournamentTeam.objects.create(tournament=tournament_obj,
                                                  team=team_obj,
                                                  source=source_obj)
    collect_extra_info.short_description = "Collect Extra Information"

    def collect_results(self, request, queryset):
        pass
    collect_results.short_description = "Collect Tournament Results"


class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'final_position')


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


class StadiumAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'team_owner', 'display_capacity')
    ordering = ('name',)

    def team_owner(self, obj):
        team_owner = obj.team_set.all()[0]
        return team_owner.name
    team_owner.short_description = 'Team Owner'

    def display_capacity(self, obj):
        if obj.capacity == -1:
            return 'Unknown'
        else:
            return utils.int_seperation_char(obj.capacity, sep_char='.')
    display_capacity.short_description = 'Capacity'


admin.site.register(Source, SourceAdmin)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(City)
admin.site.register(Stadium, StadiumAdmin)
admin.site.register(Player)
admin.site.register(Coach)
admin.site.register(Referee)
admin.site.register(Team, TeamAdmin)
admin.site.register(PlayerTeam)
admin.site.register(CoachTeam)
#admin.site.register(StadiumTeam)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentTeam, TournamentTeamAdmin)
admin.site.register(TournamentPlayer)
admin.site.register(Game, GameAdmin)
admin.site.register(GameTeam, GameTeamAdmin)
admin.site.register(GamePlayer)
admin.site.register(GameReferee)
admin.site.register(Goal)
admin.site.register(Card)
