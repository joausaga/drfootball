# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from models import Source, Country, Region, City, Stadium, Player, Coach, \
                   Referee, Team, PlayerTeam, CoachTeam, StadiumTeam, \
                   Tournament, TournamentTeam, TournamentPlayer, Game, \
                   GameTeam, GamePlayer, GameReferee, Goal, Card, SeasonTeamFinalStatus, \
                   TournamentStatus
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


def create_new_city(city_dict, region, country):
    city_name = utils.format_text_to_save_db(city_dict['name'])
    if 'wikipage' in city_dict.keys():
        if region:
            return City.objects.create(name=city_name, country=country, region=region,
                                       wikipage=city_dict['wikipage'])
        else:
            return City.objects.create(name=city_name, country=country, wikipage=city_dict['wikipage'])
    else:
        if region:
            return City.objects.create(name=city_name, country=country, region=region)
        else:
            return City.objects.create(name=city_name, country=country)


def create_new_region(region_dict, country):
    region_name = utils.format_text_to_save_db(region_dict['name'])
    if 'wikipage' in region_dict.keys():
        return Region.objects.create(name=region_name, country=country, wikipage=region_dict['wikipage'])
    else:
        return City.objects.create(name=region_name, country=country)


class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'queried')


class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'start_date', 'end_date', 'champion', 'runnerup', 'season_champion')
    actions = ['collect_extra_info', 'collect_results']

    def champion(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_position == 1:
                return tournament_team.team.name
        return ''
    champion.short_description = "Winner"

    def runnerup(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_position == 2:
                return tournament_team.team.name
        return ''

    def __get_or_create_region(self, region_dict):
        region_name = utils.normalize_text(region_dict['name'])
        region_objs = Region.objects.filter(name__icontains=region_name)
        if len(region_objs) == 0:
            # the region doesn't exist, the default country for
            # all regions will be paraguay
            country = Country.objects.get(name__iexact=DEF_COUNTRY)
            region = create_new_region(region_dict, country)
        elif len(region_objs) == 1:
            region = region_objs[0]
        elif len(region_objs) > 1:
            region = disambiguate_objs_by_name(region_objs, region_name)
        else:
            raise Exception('Error!, Dont understand the number of cities')
        return region

    def __update_city(self, city_obj, city_dict):
        if 'wikipage' in city_dict.keys():
            city_obj.wikipage = city_dict['wikipage']
        if 'region' in city_dict.keys():
            region = self.__get_or_create_region(city_dict['region'])
            city_obj.add(region)
        city_obj.save()

    def __get_or_create_city(self, city_dict):
        city_name = utils.normalize_text(city_dict['name'])
        city_objs = City.objects.filter(name__icontains=city_name)
        if len(city_objs) == 0:
            # the city doesn't exist, the default country for
            # all cities will be paraguay
            country = Country.objects.get(name__iexact=DEF_COUNTRY)
            if 'region' in city_dict:
                region = self.__get_or_create_region(city_dict['region'])
            else:
                region = None
            city = create_new_city(city_dict, region, country)
        elif len(city_objs) == 1:
            city = city_objs[0]
        elif len(city_objs) > 1:
            city = disambiguate_objs_by_name(city_objs, city_name)
        else:
            raise Exception('Dont understand the number of cities')
        self.__update_city(city, city_dict)
        return city

    def __update_stadium(self, stadium_obj, stadium_dict):
        if 'capacity' in stadium_dict.keys():
            stadium_obj.capacity = stadium_dict['capacity']
        if 'wikipage' in stadium_dict.keys():
            stadium_obj.wikipage = stadium_dict['wikipage']
        stadium_obj.save()

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
            raise Exception('Dont understand the number of stadiums')
        self.__update_stadium(stadium, stadium_dict)
        return stadium

    def __update_team(self, team_obj, team_dict):
        if 'foundation' in team_dict.keys():
            team_obj.foundation = team_dict['foundation']
        if 'wikipage' in team_dict.keys():
            team_obj.wikipage = team_dict['wikipage']
        team_obj.save()

    def __get_or_create_team(self, team, source):
        team_name = utils.normalize_text(team['name'])
        team_name = team_name.replace('club', '').strip()  # delete word 'club'
        team_objs = Team.objects.filter(name__icontains=team_name)
        stadium = None
        if len(team_objs) == 1:
            team_obj = team_objs[0]
        elif len(team_objs) > 1:
            team_obj = disambiguate_objs_by_name(team_objs, team_name)
        elif len(team_objs) == 0:
            # the team doesn't exist yet
            if 'stadium' in team.keys() and 'city' in team.keys():
                stadium = self.__get_or_create_stadium(team['stadium'], team['city'])
                team_obj = create_new_team(team, stadium)
            else:
                raise Exception('The team {0} doesnt exist and a new one cannot be created because there are not '
                                'information about city and stadium'.format(team_name))
        else:
            raise Exception('Dont understand the number of teams')
        # associate the team with its stadium in case the association
        # doesn't exists
        if stadium and not team_obj.stadium.all():
            StadiumTeam.objects.create(stadium=stadium, team=team_obj, source=source)
        self.__update_team(team_obj, team)
        return team_obj

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
            if 'season statuses' in information_collected:
                for team in tournament_info['teams']:
                    # create the teams' season final status
                    team_obj = self.__get_or_create_team(team, source_obj)
                    ss = SeasonTeamFinalStatus.objects.create(team=team_obj, season=obj.year,
                                                              position=int(team['position']),
                                                              points=int(team['points']),
                                                              games=int(team['games']),
                                                              wins=int(team['won']),
                                                              draws=int(team['drew']),
                                                              losses=int(team['lost']),
                                                              goals=int(team['gf']),
                                                              goals_conceded=int(team['gc']),
                                                              goals_difference=int(team['goals_difference']))
                    if team['international_status']:
                        for status in team['international_status']:
                            status_obj, created = TournamentStatus.objects.get_or_create(name=status)
                            ss.status.add(status_obj)
        self.message_user(request, "The action was completed successfully!")
    collect_extra_info.short_description = "Collect Extra Information"

    def collect_results(self, request, queryset):
        DEF_PREFIX_TOURNAMENT_FILE = 'campeonatos'

        for obj in queryset:
            tournament_dict = {
                'name': obj.name,
                'year': obj.year,
                'start_string': obj.start_string,
                'end_string': obj.end_string,
                'results_local_fname': '{0}{1}.html'.format(DEF_PREFIX_TOURNAMENT_FILE, obj.year)
            }
            parser_rsssf.read_championship_results(tournament_dict)
        self.message_user(request, "The action was completed successfully!")
    collect_results.short_description = "Collect Tournament Results"


class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'final_position')
    list_filter = ('tournament', )


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'foundation', 'local_championships',
                    'international_championships')
    ordering = ('name', 'foundation', 'local_championships', 'international_championships')


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


class SeasonTeamFinalStatusAdmin(admin.ModelAdmin):
    list_display = ('position', 'team', 'season', 'final_status', 'points', 'games', 'wins', 'draws',
                    'losses', 'goals', 'goals_conceded', 'goals_difference')
    ordering = ('position', 'season')
    list_filter = ('season', )

    def final_status(self, obj):
        statuses = obj.status.all()
        str_final_status = ''
        for status in statuses:
            str_final_status = status.name.title() + ' '
        return str_final_status
    final_status.short_description = 'International Status'

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
#admin.site.register(TournamentStatus)
admin.site.register(SeasonTeamFinalStatus, SeasonTeamFinalStatusAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GameTeam, GameTeamAdmin)
admin.site.register(GamePlayer)
admin.site.register(GameReferee)
admin.site.register(Goal)
admin.site.register(Card)
