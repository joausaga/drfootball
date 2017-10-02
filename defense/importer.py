
import itertools, utils, re

from collections import defaultdict
from defense.models import Player, Country, Team, \
    Stadium, City, Region, StadiumTeam, TournamentTeam, \
    GameTeam, Goal, GamePlayer, PlayerTeam
from difflib import SequenceMatcher
from django.core.exceptions import ObjectDoesNotExist


num_pattern = re.compile('[^0-9]')
DEF_COUNTRY = 'paraguay'
potential_compound_last_names = [{'last_name': 'silva', 'prefix': 'da'}]


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

###
# Person (Player, Coach)
###


def extract_firstname_lastname_from_string(name_str):
    vec_name = name_str.split(' ')
    name_length = len(vec_name)

    if name_length > 2:
        print('Found the name {0} having more than two words, took the last '
              'word as the last name'.format(utils.normalize_text(name_str)))
    # assume that the last part of the name contains the last name
    last_name = vec_name[-1].strip().lower()
    # check whether the last name can be a compound last name
    limit_name = name_length-1
    for compound_last_name in potential_compound_last_names:
        if last_name.lower() == compound_last_name['last_name'] and \
           vec_name[-2].lower() == compound_last_name['prefix']:
            last_name = vec_name[-2] + ' ' + last_name
            limit_name -= 1
            break
    # extract name
    if name_length == 1:
        first_name = ''
    else:
        first_name = utils.format_text_to_save_db(' '.join(vec_name[:limit_name]))

    return {'first_name': first_name, 'last_name': last_name}


def search_person_by_name(name):
    dict_name = extract_firstname_lastname_from_string(name)
    return Player.objects.filter(last_name__iexact=dict_name['last_name'])


def create_new_person(person_dict):
    dict_name = extract_firstname_lastname_from_string(person_dict['name'])
    person_attrs = {'first_name': dict_name['first_name'],
                    'last_name': dict_name['last_name']}
    if 'wikipage' in person_dict.keys() and person_dict['wikipage']:
        person_attrs['wikipage'] = person_dict['wikipage']
    if 'country' in person_dict.keys():
        country = Country.objects.get_or_create(name__iexact=person_dict['country'])
        person_attrs['nationality'] = country
    return Player.objects.create(**person_attrs)


def update_person(person_obj, person_dict):
    dict_name = extract_firstname_lastname_from_string(person_dict['name'])
    person_obj.first_name = dict_name['first_name']
    if 'country' in person_dict.keys():
        person_obj.nationality= person_dict['country']
    if 'wikipage' in person_dict.keys():
        person_obj.wikipage = person_dict['wikipage']
    person_obj.save()


def disambiguate_player(player_objs, tournament_obj):
    tournament_teams = tournament_obj.teams.all()
    players_str = ''
    for player_obj in player_objs:
        players_str += player_obj.name + ' '
        player_teams = player_objs.team_set.all()
        for team in player_teams:
            if team in tournament_teams:
                return player_obj
    raise Exception('Couldnt disambiguate the players ', players_str)


def get_or_create_player(tournament_obj, player_dict):
    player_name = utils.normalize_text(player_dict['name'])
    ret_obj = search_person_by_name(player_name)
    if not ret_obj:
        # the player doesn't exist yet
        player_obj = create_new_person(player_dict)
    elif len(ret_obj) > 1:
        player_obj = disambiguate_player(ret_obj, tournament_obj)
    else:
        player_obj = ret_obj[0]
    update_person(player_obj, player_dict)
    return player_obj


###
# Team
###

def create_new_team(team_dict, stadium_obj):
    team_attrs = {'name': utils.format_text_to_save_db(team_dict['name']),
                  'city': stadium_obj.city}
    if 'wikipage' in team_dict.keys():
        team_attrs['wikipage'] = team_dict['wikipage']
    return Team.objects.create(**team_attrs)


def disambiguate_team(team_objs, tournament_obj):
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


def update_team(team_obj, team_dict):
    team_name = team_dict['name'].replace('club', '').strip()  # delete word 'club'
    if len(team_name) > len(team_obj.name):
        team_obj.name = utils.format_text_to_save_db(team_dict['name'])
    if 'foundation' in team_dict.keys():
        team_obj.foundation = team_dict['foundation']
    if 'wikipage' in team_dict.keys():
        team_obj.wikipage = team_dict['wikipage']
    team_obj.save()


def get_or_create_team(tournament_obj, team, source):
    team_name = utils.normalize_text(team['name'])
    team_name = team_name.replace('club', '').strip()  # delete word 'club'
    ret_obj = search_obj_by_name(Team, team_name)
    stadium = None
    if not ret_obj:
        # the team doesn't exist yet
        if 'stadium' in team.keys() and 'city' in team.keys():
            stadium = get_or_create_stadium(team['stadium'], team['city'])
            team_obj = create_new_team(team, stadium)
        else:
            raise Exception('The team {0} doesnt exist and a new one cannot be created because there are not '
                            'information about city and stadium'.format(team_name))
    elif len(ret_obj) > 1:
        team_obj = disambiguate_team(ret_obj, tournament_obj)
    else:
        team_obj = ret_obj[0]
    # associate the team with its stadium in case the association
    # doesn't exists
    if stadium and not team_obj.stadium.all():
        StadiumTeam.objects.create(stadium=stadium, team=team_obj, source=source)
    update_team(team_obj, team)
    return team_obj


###
# Stadium
###


def create_new_stadium(stadium_dict):
    stadium_attrs = {'name': utils.format_text_to_save_db(stadium_dict['name'])}
    if 'capacity' in stadium_dict.keys():
        stadium_attrs['capacity'] = int(num_pattern.sub('', stadium_dict['capacity']))
    else:
        stadium_attrs['capacity'] = -1
    if 'wikipage' in stadium_dict.keys():
        stadium_attrs['wikipage'] = stadium_dict['wikipage']
    return Stadium.objects.create(**stadium_attrs)


def update_stadium(stadium_obj, stadium_dict):
    if len(stadium_dict['name']) > len(stadium_dict.name):
        stadium_dict.name = stadium_dict['name']
    stadium_obj.name = stadium_dict['name']
    if 'capacity' in stadium_dict.keys():
        stadium_obj.capacity = stadium_dict['capacity']
    if 'wikipage' in stadium_dict.keys():
        stadium_obj.wikipage = stadium_dict['wikipage']
    stadium_obj.save()


def get_or_create_stadium(stadium_dict, city_dict):
    stadium_name = utils.normalize_text(stadium_dict['name'])
    stadium_name = stadium_name.replace('estadio', '').strip()  # delete word 'estadio'
    ret_obj = search_obj_by_name(Stadium, stadium_name)
    if not ret_obj:
        # the stadium doesn't exist yet
        city = get_or_create_city(city_dict)
        stadium_obj = create_new_stadium(stadium_dict, city)
    elif len(ret_obj) > 0:
        raise Exception('Got more than one stadium')
    else:
        stadium_obj = ret_obj[0]
        update_stadium(stadium_obj, stadium_dict)
    return stadium_obj


###
# City
###


def create_new_city(city_dict, region):
    city_attrs = {'name': utils.format_text_to_save_db(city_dict['name'])}
    if 'wikipage' in city_dict.keys():
        city_attrs['wikipage'] = city_dict['wikipage']
    if region:
        city_attrs['region'] = region
    return City.objects.create(**city_attrs)


def update_city(city_obj, city_dict):
    if len(city_dict['name']) > len(city_obj.name):
        city_obj.name = city_dict['name']
    city_obj.name = city_dict['name']
    if 'wikipage' in city_dict.keys():
        city_obj.wikipage = city_dict['wikipage']
    if 'region' in city_dict.keys():
        region = get_or_create_region(city_dict['region'])
        city_obj.add(region)
    city_obj.save()


def get_or_create_city(city_dict):
    city_name = utils.normalize_text(city_dict['name'])
    ret_obj = search_obj_by_name(City, city_name)
    if not ret_obj:
        # the city doesn't exist, the default country for
        # all cities will be paraguay
        country = Country.objects.get(name__iexact=DEF_COUNTRY)
        if 'region' in city_dict:
            region = get_or_create_region(city_dict['region'])
        else:
            region = None
        city_obj = create_new_city(city_dict, region, country)
    elif len(ret_obj) > 1:
        raise Exception('Got more than one city')
    else:
        city_obj = ret_obj[0]
        update_city(city_obj, city_dict)
    return city_obj


###
# Region
###

def create_new_region(region_dict):
    region_attrs = {'name': utils.format_text_to_save_db(region_dict['name'])}
    if 'wikipage' in region_dict.keys():
        region_attrs['wikipage'] = region_dict['wikipage']
    return Region.objects.create(**region_attrs)


def get_or_create_region(region_dict):
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


def update_team_info_in_tournament(tournament_obj, team_obj, source_obj,
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


def add_team_game(tournament_obj, game_obj, source_obj, team_dict,
                  rival_dict, home=True):
    team_obj = get_or_create_team(tournament_obj, team_dict, source_obj)
    game_team_attrs = {
        'game': game_obj,
        'team': team_obj,
        'home': home,
        'goals': int(team_dict['score'])
    }
    game_team_obj = GameTeam.objects.create(**game_team_attrs)
    # update team info in tournament
    team_result = update_team_info_in_tournament(tournament_obj, team_obj, source_obj,
                                                 game_team_obj, team_dict, rival_dict)
    # create goal objects
    game_players = defaultdict(list)
    for goal in team_dict['goals_info']:
        player_obj = get_or_create_player(tournament_obj, {'name': goal['author']})
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


def add_players_to_tournament_list(tournament_players, players):
    for player_id, goals in players.items():
        if player_id in tournament_players.keys():
            tournament_players[player_id].extend(goals)
        else:
            tournament_players[player_id].append(goals)
    return tournament_players
