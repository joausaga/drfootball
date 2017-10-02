# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# python libraries
from collections import defaultdict
from datetime import datetime
import utils

# django modules
from django.contrib import admin, messages

# project imports
from models import Source, Country, Region, City, Stadium, Player, Coach, \
                   Referee, Team, PlayerTeam, CoachTeam, \
                   Tournament, TournamentTeam, TournamentPlayer, Game, \
                   GameTeam, GamePlayer, GameReferee, Goal, Card, SeasonTeamFinalStatus, \
                   TournamentStatus
from goalkeeper import parser_rsssf
from goalkeeper.wiki_scrapers import ParaguayanChampionshipResultsScraper, \
                                     ParaguayanTournamentScraper
from importer import get_or_create_team, get_or_create_stadium, add_team_game, \
    add_players_to_tournament_list



class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'queried')


class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'start_date', 'end_date', 'champion', 'runnerup', 'season_champion')
    actions = ['collect_extra_info', 'collect_results']
    objs_created = defaultdict(list)

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

    def __display_feedback_msg(self, request):
        if self.objs_created:
            msg = 'The action was completed successfully!\n'
            for model, objs in self.objs_created.items():
                '- It was created {0} objects of the type {1}\n'.format(model, len(objs))
            self.message_user(request, msg, level=messages.SUCCESS)
        else:
            msg = 'No objects were created'
            self.message_user(request, msg, level=messages.INFO)
        return msg

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
            if tournament_info:
                self.objs_created = {}
                information_collected = [option.strip() for option in obj.additional_info.split(';')]
                if 'teams info' in information_collected:
                    for team in tournament_info['teams']:
                        # add teams to tournament
                        team_obj = get_or_create_team(tournament_obj, team, source_obj)
                        tt_obj = TournamentTeam.objects.create(tournament=tournament_obj,
                                                               team=team_obj,
                                                               source=source_obj)
                        self.objs_created['TournamentTeam'].append(tt_obj)
                if 'season statuses' in information_collected:
                    for team in tournament_info['teams']:
                        # create the teams' season final status
                        team_obj = get_or_create_team(tournament_obj, team, source_obj)
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
                        self.objs_created['SeasonTeamFinalStatus'].append(ss)
                        if team['international_status']:
                            for status in team['international_status']:
                                status_obj, created = TournamentStatus.objects.get_or_create(name=status)
                                ss.status.add(status_obj)
                                if created:
                                    self.objs_created['TournamentStatus'].append(status_obj)
        self.__display_feedback_msg(request)
    collect_extra_info.short_description = 'Collect Extra Information'

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
                self.objs_created = {}
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
                            game_attrs['stadium'] = get_or_create_stadium(stadium_dict, city_dict)
                        if 'stage' in game.keys():
                            game_attrs['stage'] = game['stage']
                        game_obj = Game.objects.create(**game_attrs)
                        game_obj.source.add(source_obj)
                        self.objs_created['Game'].append(game_obj)
                        # add home team to game
                        game_players = add_team_game(tournament_obj, game_obj, source_obj,
                                                     game['home_team'], game['away_team'],
                                                     home=True)
                        tournament_players = add_players_to_tournament_list(tournament_players,
                                                                            game_players)
                        # add away team to game
                        game_players = add_team_game(tournament_obj, game_obj, source_obj,
                                                     game['away_team'], game['home_team'],
                                                     home=False)
                        tournament_players = add_players_to_tournament_list(tournament_players,
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
        team_owner = obj.team_set.all()
        if len(team_owner) > 0:
            return team_owner[0].name
        else:
            return 'Unknown'
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
    ordering = ('position', )
    list_filter = ('season', )

    def final_status(self, obj):
        statuses = obj.status.all()
        str_final_status = ''
        for status in statuses:
            str_final_status = status.name.title() + ' '
        return str_final_status
    final_status.short_description = 'Final Status'


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
    list_filter = ('tournament', )
    ordering = ('-goals', 'player', )


class PlayerTeamAdmin(admin.ModelAdmin):
    list_display = ('player', 'team', 'games', 'wins', 'draws', 'losses', 'goals', 'cards')


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    ordering = ('first_name', 'last_name')


admin.site.register(Source, SourceAdmin)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(City)
admin.site.register(Stadium, StadiumAdmin)
admin.site.register(Player, PlayerAdmin)
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
