# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# python libraries
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import itertools
import re
import pytz

# django modules
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist

# project imports
from models import Source, Country, Region, City, Stadium, Player, Coach, \
                   Referee, Team, PlayerTeam, CoachTeam, StadiumTeam, \
                   Tournament, TournamentTeam, TournamentPlayer, Game, \
                   GameTeam, GamePlayer, GameReferee, Goal, Card, SeasonTeamFinalStatus, \
                   TournamentStatus

import utils
from goalkeeper import parser_rsssf
from goalkeeper.wiki_scrapers import ParaguayanChampionshipResultsScraper, \
                                     ParaguayanTournamentScraper


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


def search_most_similar_strings(model, name):
    threshold = 0.50
    objs_to_return = []
    model_objs = model.objects.all()
    similar_ratios = []
    for obj in model_objs:
        similar_ratios.append(SequenceMatcher(None, name, obj.name).ratio())
    if similar_ratios:
        max_ratios = max(similar_ratios)
        if max_ratios > threshold:
            size_vec_sim = len(similar_ratios)
            for i in range(0, size_vec_sim):
                if similar_ratios[i] == max_ratios:
                    objs_to_return.append(model_objs[i])
    return objs_to_return

def search_obj_by_name(model, name):
    nor_name = utils.normalize_text(name).strip()
    objs_to_return = model.objects.filter(name__icontains=nor_name)
    if len(objs_to_return) == 1:
        return objs_to_return
    else:
        if len(objs_to_return) == 0:
            objs_to_return = search_most_similar_strings(model, nor_name)
        if len(objs_to_return) > 1:
            objs_to_return = [disambiguate_objs_by_name(objs_to_return, nor_name)]
    return objs_to_return


def create_new_person(person_dict):
    person_attrs = {'name': utils.format_text_to_save_db(person_dict['name'])}
    if 'wikipage' in person_dict.keys() and person_dict['wikipage']:
        person_attrs['wikipage'] = person_dict['wikipage']
    if 'country' in person_dict.keys():
        country = Country.objects.get_or_create(name__iexact=person_dict['country'])
        person_attrs['nationality'] = country
    return Player.objects.create(**person_attrs)


def update_person(person_obj, person_dict):
    if 'country' in person_dict.keys():
        person_obj.nationality= person_dict['country']
    if 'wikipage' in person_dict.keys():
        person_obj.wikipage = person_dict['wikipage']
    person_obj.save()


def create_new_team(team_dict, stadium_obj):
    team_attrs = {'name': utils.format_text_to_save_db(team_dict['name']),
                  'city': stadium_obj.city}
    if 'wikipage' in team_dict.keys():
        team_attrs['wikipage'] = team_dict['wikipage']
    return Team.objects.create(**team_attrs)


def create_new_stadium(stadium_dict, city):
    stadium_attrs = {'name': utils.format_text_to_save_db(stadium_dict['name'])}
    if 'capacity' in stadium_dict.keys():
        stadium_attrs['capacity'] = int(num_pattern.sub('', stadium_dict['capacity']))
    else:
        stadium_attrs['capacity'] = -1
    if 'wikipage' in stadium_dict.keys():
        stadium_attrs['wikipage'] = stadium_dict['wikipage']
    return Stadium.objects.create(**stadium_attrs)


def create_new_city(city_dict, region, country):
    city_attrs = {'name': utils.format_text_to_save_db(city_dict['name'])}
    if 'wikipage' in city_dict.keys():
        city_attrs['wikipage'] = city_dict['wikipage']
    if region:
        city_attrs['region'] = region
    return City.objects.create(**city_attrs)


def create_new_region(region_dict, country):
    region_attrs = {'name': utils.format_text_to_save_db(region_dict['name'])}
    if 'wikipage' in region_dict.keys():
        region_attrs['wikipage'] = region_dict['wikipage']
    return Region.objects.create(**region_attrs)


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
        ret_objs = search_obj_by_name(Region, region_name)
        if not ret_objs:
            # the region doesn't exist, the default country for
            # all regions will be paraguay
            country = Country.objects.get(name__iexact=DEF_COUNTRY)
            region_obj = create_new_region(region_dict, country)
        elif len(ret_objs) > 1:
            raise Exception('Got more than one region')
        else:
            region_obj = ret_objs[0]
        return region_obj

    def __update_city(self, city_obj, city_dict):
        if len(city_dict['name']) > len(city_obj.name):
            city_obj.name = city_dict['name']
        city_obj.name = city_dict['name']
        if 'wikipage' in city_dict.keys():
            city_obj.wikipage = city_dict['wikipage']
        if 'region' in city_dict.keys():
            region = self.__get_or_create_region(city_dict['region'])
            city_obj.add(region)
        city_obj.save()

    def __get_or_create_city(self, city_dict):
        city_name = utils.normalize_text(city_dict['name'])
        ret_obj = search_obj_by_name(City, city_name)
        if not ret_obj:
            # the city doesn't exist, the default country for
            # all cities will be paraguay
            country = Country.objects.get(name__iexact=DEF_COUNTRY)
            if 'region' in city_dict:
                region = self.__get_or_create_region(city_dict['region'])
            else:
                region = None
            city_obj = create_new_city(city_dict, region, country)
        elif len(ret_obj) > 1:
            raise Exception('Got more than one city')
        else:
            city_obj = ret_obj[0]
            self.__update_city(city_obj, city_dict)
        return city_obj

    def __update_stadium(self, stadium_obj, stadium_dict):
        if len(stadium_dict['name']) > len(stadium_dict.name):
            stadium_dict.name = stadium_dict['name']
        stadium_obj.name = stadium_dict['name']
        if 'capacity' in stadium_dict.keys():
            stadium_obj.capacity = stadium_dict['capacity']
        if 'wikipage' in stadium_dict.keys():
            stadium_obj.wikipage = stadium_dict['wikipage']
        stadium_obj.save()

    def __get_or_create_stadium(self, stadium_dict, city_dict):
        stadium_name = utils.normalize_text(stadium_dict['name'])
        stadium_name = stadium_name.replace('estadio', '').strip()  # delete word 'estadio'
        ret_obj = search_obj_by_name(Stadium, stadium_name)
        if not ret_obj:
            # the stadium doesn't exist yet
            city = self.__get_or_create_city(city_dict)
            stadium_obj = create_new_stadium(stadium_dict, city)
        elif len(ret_obj) > 0:
            raise Exception('Got more than one staidum')
        else:
            stadium_obj = ret_obj[0]
            self.__update_stadium(stadium_obj, stadium_dict)
        return stadium_obj

    def __disambiguate_team(self, team_objs, tournament_obj):
        teams_str = ''
        for team_obj in team_objs:
            teams_str += team_obj.name + ' '
            try:
                team_tournament_obj = TournamentTeam.objects.get(tournament=tournament_obj,
                                                                 team=team_obj)
                return team_tournament_obj.team
            except ObjectDoesNotExist:
                continue
        raise Exception('Couldnt disambiguate the teams ', teams_str)

    def __update_team(self, team_obj, team_dict):
        if len(team_dict['name']) > len(team_obj.name):
            team_obj.name = team_dict['name']
        if 'foundation' in team_dict.keys():
            team_obj.foundation = team_dict['foundation']
        if 'wikipage' in team_dict.keys():
            team_obj.wikipage = team_dict['wikipage']
        team_obj.save()

    def __get_or_create_team(self, tournament_obj, team, source):
        team_name = utils.normalize_text(team['name'])
        team_name = team_name.replace('club', '').strip()  # delete word 'club'
        ret_obj = search_obj_by_name(Team, team_name)
        stadium = None
        if not ret_obj:
            # the team doesn't exist yet
            if 'stadium' in team.keys() and 'city' in team.keys():
                stadium = self.__get_or_create_stadium(team['stadium'], team['city'])
                team_obj = create_new_team(team, stadium)
            else:
                raise Exception('The team {0} doesnt exist and a new one cannot be created because there are not '
                                'information about city and stadium'.format(team_name))
        elif len(ret_obj) > 1:
            team_obj = self.__disambiguate_team(ret_obj, tournament_obj)
        else:
            team_obj = ret_obj[0]
        # associate the team with its stadium in case the association
        # doesn't exists
        if stadium and not team_obj.stadium.all():
            StadiumTeam.objects.create(stadium=stadium, team=team_obj, source=source)
        self.__update_team(team_obj, team)
        return team_obj

    def __disambiguate_player(self, player_objs, tournament_obj):
        tournament_teams = tournament_obj.teams.all()
        players_str = ''
        for player_obj in player_objs:
            players_str += player_obj.name + ' '
            player_teams = player_objs.team_set.all()
            for team in player_teams:
                if team in tournament_teams:
                    return player_obj
        raise Exception('Couldnt disambiguate the players ', players_str)

    def __get_or_create_player(self, tournament_obj, player_dict):
        player_name = utils.normalize_text(player_dict['name'])
        ret_obj = search_obj_by_name(Player, player_name)
        if not ret_obj:
            # the player doesn't exist yet
            player_obj = create_new_person(player_dict)
        elif len(ret_obj) > 1:
            player_obj = self.__disambiguate_player(ret_obj, tournament_obj)
        else:
            player_obj = ret_obj[0]
        update_person(player_obj, player_dict)
        return player_obj

    def __update_team_info_in_tournament(self, tournament_obj, team_obj, source_obj,
                                         game_team_obj, team_dict, rival_dict):
        try:
            tournament_team_obj = TournamentTeam.objects.get(tournament=tournament_obj,
                                                             team=team_obj)
        except ObjectDoesNotExist:
            tournament_team_obj = TournamentTeam.objects.create(tournament=tournament_obj,
                                                                team=team_obj,
                                                                source=source_obj)
        tournament_team_obj.games += 1
        if game_team_obj.goals > int(rival_dict['score']):
            team_result = 'won'
            tournament_team_obj.wins += 1
        elif game_team_obj.goals == int(rival_dict['score']):
            team_result = 'drew'
            tournament_team_obj.draws += 1
        else:
            team_result = 'lost'
            tournament_team_obj.losses += 1
        tournament_team_obj.goals += len(team_dict['goals_info'])
        tournament_team_obj.goals_conceded += len(rival_dict['goals_info'])
        tournament_team_obj.points = (3 * tournament_team_obj.wins) + tournament_team_obj.draws
        tournament_team_obj.save()
        return team_result

    def __add_team_game(self, tournament_obj, game_obj, source_obj, team_dict,
                        rival_dict, home=True):
        team_obj = self.__get_or_create_team(tournament_obj, team_dict, source_obj)
        game_team_attrs = {
            'game': game_obj,
            'team': team_obj,
            'home': home,
            'goals': int(team_dict['score'])
        }
        game_team_obj = GameTeam.objects.create(**game_team_attrs)
        # update team info in tournament
        team_result = self.__update_team_info_in_tournament(tournament_obj, team_obj, source_obj,
                                                            game_team_obj, team_dict, rival_dict)
        # create goal models
        game_players = defaultdict(list)
        for goal in team_dict['goals_info']:
            player_obj = self.__get_or_create_player(tournament_obj, {'name': goal['author']})
            goal_attrs = {
                'author': player_obj,
                'minute': int(goal['minute']),
                'game': game_obj
            }
            if goal['type']:
                if goal['type'] == 'penalty':
                    goal_attrs['type'] = 'penalty'
                if goal['type'] == 'own goal':
                    goal_attrs['own'] = True
            goal_obj = Goal.objects.create(**goal_attrs)
            goal_obj.source.add(source_obj)
            # create/update game player models
            try:
                game_player_obj = GamePlayer.objects.get(game=game_obj, player=player_obj)
                game_player_obj.goals += 1
                game_player_obj.save()
            except ObjectDoesNotExist:
                game_player_attrs = {
                    'game': game_obj,
                    'player': player_obj,
                    'goals': 1
                }
                game_player_obj = GamePlayer.objects.create(**game_player_attrs)
                game_player_obj.source.add(source_obj)
            # create/update team player models
            try:
                team_player_obj = PlayerTeam.objects.get(player=player_obj)
                if player_obj.id not in game_players.keys():
                    team_player_obj.games += 1
                    if team_result == 'won':
                        team_player_obj.wins += 1
                    elif team_result == 'drew':
                        team_player_obj.draws += 1
                    else:
                        team_player_obj.losses += 1
                team_player_obj.goals += 1
                team_player_obj.save()
            except ObjectDoesNotExist:
                team_player_attrs = {
                    'player': player_obj,
                    'team': team_obj,
                    'games': 1,
                    'goals': 1
                }
                if team_result == 'won':
                    team_player_attrs['wins'] = 1
                elif team_result == 'drew':
                    team_player_attrs['draws'] = 1
                else:
                    team_player_attrs['losses'] = 1
                player_team_obj = PlayerTeam.objects.create(**team_player_attrs)
                player_team_obj.source.add(source_obj)
            game_players[player_obj.id].append(goal)
        return game_players

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
                    team_obj = self.__get_or_create_team(tournament_obj, team, source_obj)
                    TournamentTeam.objects.create(tournament=tournament_obj,
                                                  team=team_obj,
                                                  source=source_obj)
            if 'season statuses' in information_collected:
                for team in tournament_info['teams']:
                    # create the teams' season final status
                    team_obj = self.__get_or_create_team(tournament_obj, team, source_obj)
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

    def __add_players_to_tournament_list(self, tournament_players, players):
        for player_id, goals in players.items():
            if player_id in tournament_players.keys():
                tournament_players[player_id].extend(goals)
            else:
                tournament_players[player_id].append(goals)
        return tournament_players

    def collect_results(self, request, queryset):
        def_prefix_tournament_file = 'campeonatos'
        def_city = 'Asuncion'

        for obj in queryset:
            tournament_players = defaultdict(list)
            tournament_obj = obj
            source_obj = tournament_obj.source.all()[0]
            tournament_dict = {
                'name': obj.name,
                'year': obj.year,
                'start_string': obj.start_string,
                'end_string': obj.end_string,
                'results_local_file_name': '{0}{1}.html'.format(def_prefix_tournament_file, obj.year),
                'num_teams': obj.number_of_teams
            }
            if int(obj.year) <= 2007:
                results_tournament = parser_rsssf.get_data(tournament_dict)
            else:
                res_scraper = ParaguayanChampionshipResultsScraper(source_obj.url)
                results_tournament = res_scraper.collect_championship_results(tournament_dict)
            for result in results_tournament:
                if isinstance(result, dict):   # tournaments <= 2007
                    for game in result['games']:
                        game_attrs = {
                            'tournament': tournament_obj,
                            'round': result['round']
                        }
                        if game['date']:
                            game_attrs['datetime'] = datetime.strptime(game['date'], '%Y-%m-%d')
                        if 'stadium' in game.keys() and game['stadium']:
                            stadium_dict = {'name': game['stadium']}
                            city_dict = {'name': def_city}
                            game_attrs['stadium'] = self.__get_or_create_stadium(stadium_dict, city_dict)
                        game_obj = Game.objects.create(**game_attrs)
                        game_obj.source.add(source_obj)
                        # add home team to game
                        game_players = self.__add_team_game(tournament_obj, game_obj, source_obj,
                                                            game['home_team'], game['away_team'],
                                                            home=True)
                        tournament_players = self.__add_players_to_tournament_list(tournament_players,
                                                                                   game_players)
                        # add away team to game
                        game_players = self.__add_team_game(tournament_obj, game_obj, source_obj,
                                                            game['away_team'], game['home_team'],
                                                            home=False)
                        tournament_players = self.__add_players_to_tournament_list(tournament_players,
                                                                                   game_players)
                else:  # tournaments > 2007
                    pass
            # create tournament player models
            for player_id, goals in tournament_players.items():
                player_obj = Player.objects.get(id=player_id)
                tournament_player_attrs = {
                    'tournament': tournament_obj,
                    'player': player_obj,
                    'goals': len(goals)
                }
                tp = TournamentPlayer.objects.create(**tournament_player_attrs)
                tp.source.add(source_obj)
            # update the final position of teams in tournament
            t_teams = TournamentTeam.objects.filter(tournament=tournament_obj).order_by('-points')
            pos = 1
            for team in t_teams:
                team.final_position = pos
                team.save()
                pos += 1
        self.message_user(request, "The action was completed successfully!")
    collect_results.short_description = "Collect Tournament Results"


class TournamentTeamAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'team', 'points', 'games', 'wins', 'draws', 'losses',
                    'goals', 'goals_conceded', 'cards', 'final_position')
    list_filter = ('tournament', )
    ordering = ('-points', )

class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'foundation', 'local_championships',
                    'international_championships')
    ordering = ('name', 'foundation', 'local_championships', 'international_championships')


class GameAdmin(admin.ModelAdmin):
    list_display = ('game_date', 'game_time', 'game_stadium', 'tournament',
                    'home', 'away', 'score', 'round')
    ordering = ('tournament', )
    list_filter = ('tournament', )

    def game_date(self, obj):
        if obj.datetime:
            return obj.datetime.date()
        else:
            return 'Unknown'

    def game_time(self, obj):
        if not obj.datetime or \
           (obj.datetime.hour == 0 and
            obj.datetime.minute == 0):
            return 'Unknown'
        else:
            return obj.datetime.time()

    def game_stadium(self, obj):
        if obj.stadium is None:
            return 'Unknown'
        else:
            return obj.stadium

    def home(self, obj):
        game_teams = obj.teams.all()
        game_team1 = GameTeam.objects.get(game=obj, team=game_teams[0])
        if game_team1.home:
            return game_teams[0].name
        else:
            return game_teams[1].name

    def away(self, obj):
        game_teams = obj.teams.all()
        game_team1 = GameTeam.objects.get(game=obj, team=game_teams[0])
        if game_team1.home:
            return game_teams[1].name
        else:
            return game_teams[0].name

    def score(self, obj):
        game_teams = obj.teams.all()
        game_team1 = GameTeam.objects.get(game=obj, team=game_teams[0])
        game_team2 = GameTeam.objects.get(game=obj, team=game_teams[1])
        if game_team1.home:
            score_home = game_team1.goals
            score_away = game_team2.goals
        else:
            score_away = game_team1.goals
            score_home = game_team2.goals
        ret = '%s - %s' % (score_home, score_away)
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


class GoalAdmin(admin.ModelAdmin):
    list_display = ('author', 'nationality', 'minute_display', 'type_display', 'game')
    list_filter = ('author', )

    def minute_display(self, obj):
        if obj.minute < 0:
            return 'Unknown'
        else:
            return obj.minute
    minute_display.short_description = 'Minute'

    def type_display(self, obj):
        if not obj.type:
            return 'Unknown'
        else:
            return obj.type
    type_display.short_description = 'Type'

    def nationality(self, obj):
        if not obj.author.nationality:
            return 'Unknown'
        else:
            return obj.author.nationality


class GamePlayerAdmin(admin.ModelAdmin):
    list_display = ('player', 'game', 'goals', 'cards')


class TournamentPlayerAdmin(admin.ModelAdmin):
    list_display = ('player', 'tournament', 'goals', 'cards')


class PlayerTeamAdmin(admin.ModelAdmin):
    list_display = ('player', 'team', 'games', 'wins', 'draws', 'losses', 'goals', 'cards')


admin.site.register(Source, SourceAdmin)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(City)
admin.site.register(Stadium, StadiumAdmin)
admin.site.register(Player)
admin.site.register(Coach)
admin.site.register(Referee)
admin.site.register(Team, TeamAdmin)
admin.site.register(PlayerTeam, PlayerTeamAdmin)
admin.site.register(CoachTeam)
#admin.site.register(StadiumTeam)
admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentTeam, TournamentTeamAdmin)
admin.site.register(TournamentPlayer, TournamentPlayerAdmin)
#admin.site.register(TournamentStatus)
admin.site.register(SeasonTeamFinalStatus, SeasonTeamFinalStatusAdmin)
admin.site.register(Game, GameAdmin)
#admin.site.register(GameTeam, GameTeamAdmin)
admin.site.register(GamePlayer, GamePlayerAdmin)
admin.site.register(GameReferee)
admin.site.register(Goal, GoalAdmin)
admin.site.register(Card)
