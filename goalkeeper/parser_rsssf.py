# -*- coding: utf-8 -*-s

__author__ = 'jorgesaldivar'

import re, codecs, utils
from datetime import date

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

alpha_pattern = re.compile(r'[^A-Za-záéíóúñ\s]', re.UNICODE)
num_pattern = re.compile('[^0-9]')
alphanum_pattern = re.compile('[^\s\w]', re.UNICODE)
not_num_pattern = re.compile('[0-9]')


def extract_number(str):
    return int(''.join([s for s in str if s.isdigit()]))


def is_date_in_line(line):
    line_tokens = line.split(' ')
    for line_token in line_tokens:
        line_token = alpha_pattern.sub('', line_token)
        for m in months:
            if m == line_token.lower():
                return True
    return False


def get_game_date(line, date_round, year):
    if is_date_in_line(line):
        return get_round_date(line, year)
    else:
        return date_round


def get_game_info(line, date_round, year, stadium=''):
    line = " ".join(line.split())
    line_result = line.split(' ')
    home_team, away_team = [], []
    found_result = False
    home_goals, away_goals = 0, 0
    pen_home, pen_away = 0, 0
    penalties = 'pen' in line
    for element in line_result:
        if '-' in element:
            if not found_result:
                found_result = True
                home_goals = extract_number(element.split('-')[0])
                away_goals = extract_number(element.split('-')[1])
            else:
                if penalties:
                    pen_home = extract_number(element.split('-')[0])
                    pen_away = extract_number(element.split('-')[1])
                    break
        else:
            if '[' not in element and ']' not in element and \
               '(' not in element and ')' not in element:
                if not found_result:
                    home_team.append(element.strip())
                else:
                    away_team.append(element.strip())
            else:
                break
    home_team = ' '.join(home_team)
    away_team = ' '.join(away_team)

    line_last_part = line[line.find(away_team)+len(away_team):len(line)].strip()
    date_game = get_game_date(line_last_part, date_round, year)

    game = {'date': date_game, 'stadium': stadium,
            'home_team': {'name': home_team, 'score': int(home_goals),
                          'goals_info': []},
            'away_team': {'name': away_team, 'score': int(away_goals),
                          'goals_info': []}}
    if penalties:
        game['home_team']['penalties_home'] = pen_home
        game['away_team']['penalties_away'] = pen_away
    return game


def is_a_game(line):
    line = line.replace(' ', '')
    if line and line[0] != '[':
        return True
    else:
        return False


def format_txt(text):
    return utils.to_unicode(text.replace('\r\n', '').replace('\n', ''))


def to_month_number(month_letter):
    month_letter = month_letter.lower()
    return months.index(month_letter) + 1


def get_round_date(line, year):
    reg_exp_open = ''
    reg_exp_close = ''

    if '[' in line:
        reg_exp_open = '\['
        reg_exp_close = '\]'
    elif '(' in line:
        reg_exp_open = '\('
        reg_exp_close = '\)'
    if reg_exp_open != '' and \
       reg_exp_close != '':
        line_segments = line.strip().split(' ')
        # search month in line
        month, i, idx_month = '', 0, 0
        while i < len(line_segments):
            segment = alpha_pattern.sub('', line_segments[i]).lower()
            for m in months:
                if m == segment:
                    month = segment
                    idx_month = i
                    i = len(line_segments)
                    break
            i += 1
        # get day
        days = line_segments[idx_month+1]
        if '-' in days:
            days_vec = days.split('-')
            try:
                day = int(num_pattern.sub('', days_vec[1]))
            except ValueError:
                day = int(num_pattern.sub('', days_vec[0]))
        else:
            if ',' in days:
                days_vec = days.split(',')
                try:
                    day = int(num_pattern.sub('', days_vec[1]))
                except ValueError:
                    day = int(num_pattern.sub('', days_vec[0]))
            else:
                day = int(num_pattern.sub('', days))
        try:
            return date(int(year), int(to_month_number(month)), int(day)).isoformat()
        except Exception as e:
            return None
    else:
        return None


def is_a_round_line(line, next_line, year):
    if 'round' in line.lower() or \
       'first leg' in line.lower() or \
       'second leg' in line.lower():
        return True
    elif 'semifinals' in line.lower() and \
         next_line != '':
        return True
    elif 'playoff for third libertadores place' in line.lower() and \
         year == '1999':
        return True
    elif 'runners-up playoff' in line.lower() and year == '2001':
        return True
    elif 'playoff for copa sudamericana 2006' in line.lower() and year == '2005':
        return True
    else:
        return False


def update_championship_stage(line, current_stage):
    if 'liguilla' in line.lower() or \
       'cuadrangulares' in line.lower() or \
       'quarterfinals' in line.lower():
        return 'playoff'
    elif 'semifinals' in line.lower():
        return 'semifinals'
    elif 'final' in line.lower() or \
         'championship playoff' in line.lower():
        return 'final'
    else:
        return current_stage


def get_alpha_characters(raw_str):
    raw_str = alphanum_pattern.sub('', raw_str)
    raw_str = not_num_pattern.sub('', raw_str)
    return raw_str


def process_goals(goals_raw):
    goals_vec = []
    for goal_raw in goals_raw.split(','):
        # remove leading and trailing whitespaces
        goal_raw = goal_raw.strip()
        # remove every character that isn't number or letter
        goal_raw = alphanum_pattern.sub('', goal_raw)
        if goal_raw != '':
            # set default type of goal and the default time scored by a player
            type_goal, times_scored = '', 1
            # consider the case in which there is a number between parenthesis that
            # indicates that a player scored more than one goal
            if '(' in goal_raw and ')' in goal_raw:
                try:
                    times_scored = int(goal_raw[goal_raw.find('(')+1:goal_raw.find(')')])
                    goal_raw = goal_raw[:goal_raw.find('(')].strip() + goal_raw[goal_raw.find(')')+1:].strip()
                except ValueError:
                    pass
            try:
                minute = extract_number(goal_raw)
            except ValueError:
                minute = -1
            # consider own goals
            # e.g., M. Acosta 31 og
            if 'og' in goal_raw:
                type_goal = 'own goal'
                goal_raw = goal_raw.replace('og', '').strip()
            # consider penalty goals
            # e.g., F. Caballero 90 pk or F. Esteche 19pen
            if 'pk' in goal_raw or 'pen' in goal_raw:
                type_goal = 'penalty'
                goal_raw = goal_raw.replace('pk', '').strip()  # Remove reference to penalty
                goal_raw = goal_raw.replace('pen', '').strip()  # Remove reference to penalty
            # consider the case when a single player score more than one goal
            # e.g., J. Paredes 30, 77
            if not goal_raw.isdigit():
                author = get_alpha_characters(goal_raw)
            # consider a very special case of penalty with the p at the end
            # e.g., Aristides Masi 8p
            if author[-1] == 'p' and author[-2] == ' ':
                type_goal = 'penalty'
                author = author[:-2].strip()
            for ts in range(0, times_scored):
                goals_vec.append(
                    {'author': author.strip(),
                     'minute': minute,
                     'type': type_goal}
                )
    return goals_vec


def get_goal_info(line, game):
    ch_split = ''
    if ';' in line:
        ch_split = ';'
    if '/' in line:
        ch_split = '/'
    if ch_split != '':
        goals = line.split(ch_split)
        game['home_team']['goals_info'].extend(process_goals(goals[0]))
        game['away_team']['goals_info'].extend(process_goals(goals[1]))
    else:
        if len(game['home_team']['goals_info']) < game['home_team']['score']:
            game['home_team']['goals_info'].extend(process_goals(line))
        elif len(game['away_team']['goals_info']) < game['away_team']['score']:
            game['away_team']['goals_info'].extend(process_goals(line))
        else:
            print('Dont understand this goal info %', line)


def read_championship_results(championship):
    results_fname = '../data/' + championship['results_local_fname']
    in_round = False
    championship_games = []
    num_round = -1
    start_pointer, end_pointer = championship['start_string'], championship['end_string']
    date_round = ''
    championship_year = championship['year']
    championship_stage = 'regular_season'
    stadium = ''
    in_championship_section = True if start_pointer == '' else False
    reading_game_goals_info = False
    debug = False

    with codecs.open(results_fname, 'rb', encoding='ISO-8859-1') as file:
        lines = file.readlines()
        file.close()

    total_lines = len(lines)
    for num_line in range(0, total_lines):
        line = lines[num_line]
        line = format_txt(line)
        next_line = format_txt(lines[num_line+1]) if num_line+1 < total_lines else line
        if start_pointer in line.lower():
            in_championship_section = True
        if in_championship_section and end_pointer in line.lower():
            break
        if in_championship_section:
            championship_stage = update_championship_stage(line, championship_stage)
            if in_round:
                if line.strip() == '':
                    in_round = False
                    continue
                else:
                    if '-' in line:  # the line contains the result of a game
                        game_info = get_game_info(line, date_round, championship_year, stadium)
                        championship_games[num_round]['games'].append(game_info)
                    elif u'\x96' in line:
                        line = line.replace(u'\x96', '-')
                        game_info = get_game_info(line, date_round, championship_year, stadium)
                        championship_games[num_round]['games'].append(game_info)
                    else:
                        # if the line doesnt contain a game result, it could contain
                        # the date of games or data about a game's goal situations
                        if is_date_in_line(line):
                            date_round = get_round_date(line, championship_year)
                        elif '[' in line and ']' in line:
                            reading_game_goals_info = False
                            try:
                                get_goal_info(line, championship_games[num_round]['games'][-1])
                            except IndexError:
                                print('Dont understand the line %s', line)
                        elif '[' in line :
                            reading_game_goals_info = True
                            try:
                                get_goal_info(line, championship_games[num_round]['games'][-1])
                            except IndexError:
                                print('Dont understand the line %s', line)
                        elif ']' in line and reading_game_goals_info:
                            reading_game_goals_info = False
                            try:
                                get_goal_info(line, championship_games[num_round]['games'][-1])
                            except IndexError:
                                print('Dont understand the line %s', line)
                        elif reading_game_goals_info:
                            try:
                                get_goal_info(line, championship_games[num_round]['games'][-1])
                            except IndexError:
                                print('Dont understand the line %s', line)
                        elif 'bye' in line:
                            continue
                        else:
                            print('Dont understand the line %s', line)
            if is_a_round_line(line, next_line, championship_year):
                date_round = get_round_date(line, championship_year)
                # consider the case when the stadium is mentioned in the round line
                # e.g., First Leg [May 18, Defensores del Chaco]
                if date_round and ',' in line and championship_stage == 'final':
                    stadium = get_alpha_characters(line.split(',')[1].strip())
                num_round += 1
                championship_games.append({'tournament': championship['name'], 'stage': championship_stage,
                                           'round': num_round+1, 'games': []})
                in_round = True
                continue

    return championship_games


def get_data(championship):
    return read_championship_results(championship)

# if __name__ == '__main__':
#     dict_championships = []
#     meta_championships = read_championships_file('data/campeonatos.csv')
#     for meta_championship in meta_championships:
#         if int(meta_championship['year']) <= 2007:
#             print('Championship %s', meta_championship['name'])
#             dict_championships.append(read_championship_results(meta_championship))
#         else:
#             print('here')
#     print ('Finished!')