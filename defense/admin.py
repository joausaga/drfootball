# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from models import Source, Country, Region, City, Stadium, Player, Coach, \
                   Referee, Team, PlayerTeam, CoachTeam, StadiumTeam, \
                   Tournament, TournamentTeam, TournamentPlayer, Game, \
                   GameTeam, GamePlayer, GameReferee, Goal, Card
from django.contrib import admin

# Register your models here.


class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'queried')


class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'start_date', 'end_date', 'champion', 'runnerup')

    def champion(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_status == 'champion':
                return tournament_team.team.name
        return ''

    def runnerup(self, obj):
        tournament_teams = obj.tournamentteam_set.all()
        for tournament_team in tournament_teams:
            if tournament_team.final_status == 'runnerup':
                return tournament_team.team.name
        return ''


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
        #ret = '%s %s - %s %s' % (game_teams[home_idx].team.name, game_teams[home_idx].goals,
        #                         game_teams[away_idx].goals, game_teams[away_idx].team.name)
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
