# -*- coding: utf-8 -*-s

__author__ = 'jorgesaldivar'

import requests, utils, pytz, re
from bs4 import BeautifulSoup, NavigableString
from datetime import date, datetime

# Background color
YELLOW_HEX = '#ffcc00;'
DARK_YELLOW_HEX = '#ffff00'
LIGHT_YELLOW_HEX = '#f0e68c'
ORANGE_HEX = '#ffd700'
PINK_HEX = '#ffcccc;'
BLUE_HEX = '#00ccff;'
LIGHT_BLUE_HEX = '#87cefa'
LIGHT_BLUE_HEX2 = '#afeeee'
GREEN_HEX = '#90ee90'
LIGHT_GREEN_HEX = '#ccff00;'
LIGHT_GREEN_HEX2 = '#adff2f'
DARK_GREEN_HEX = '#66cdaa'
GREEN_HEX2 = '#32cd32'
RED_HEX = '#ff4444;'


class ParaguayanChampionshipResultsScraper:
    url = ''
    dom = None
    py_timezone = pytz.timezone("America/Asuncion")
    prefix_url = 'https://es.wikipedia.org'
    num_pattern = ''
    alpha_pattern = ''

    def __init__(self, url):
        self.url = url
        self.num_pattern = re.compile('[^0-9]')
        self.alpha_pattern = re.compile(r'[^A-Za-z\s]', re.UNICODE)

    def collect_championship_results(self, championship):
        ret_rq = requests.get(self.url)
        fixture_results = []
        if ret_rq.status_code == 200:
            self.dom = BeautifulSoup(ret_rq.text, 'html.parser')
            championship_year = championship['year']
            if int(championship_year) <= 2016:
                fixture_tables = self.__get_fixture_tables()
                for fixture_table in fixture_tables:
                    fixture_results.append(self.__process_fixture_table(fixture_table, championship_year))
            else:
                fixture_results = self.__read_results_new_format(championship['num_teams'])
        return fixture_results

    def __process_datetime_new_format(self, cell_content):
        raw_dt = cell_content.split(',')
        # process date
        raw_date = raw_dt[0]
        idx_de = raw_date.rfind(' de ')
        day_month = raw_date[0:idx_de]
        date_year = raw_date[idx_de+1:len(raw_date)].split('de')[1].strip()
        game_date = self.__process_game_date(day_month, date_year)
        # process date and timer
        raw_time = raw_dt[1].strip()
        game_time = datetime.strptime(raw_time, '%H:%M')
        game_date = datetime.strptime(game_date, '%Y-%m-%d')
        game_datetime = datetime(game_date.year, game_date.month, game_date.day,
                                 game_time.hour, game_time.minute, game_time.second)
        return game_datetime

    def __process_goal_new_format(self, cell_content, num_goals):
        count_element = 1
        author_goal, type_goal, minute_goal = '', '', ''
        goals = []
        for child in cell_content.contents:
            if child.name == 'br':
                goals.append(
                    {'author': author_goal,
                     'type': type_goal,
                     'minute': minute_goal}
                )
                count_element = 1
                type_goal = minute_goal = ''
            else:
                if count_element == 1:
                    if type(child) == NavigableString:
                        if child != '\n':
                            author_goal = child
                    else:
                        author_goal = child.get_text(strip=True).lower()
                else:
                    if child.name == 'span':
                        if minute_goal:
                            goals.append(
                                {'author': author_goal,
                                 'type': type_goal,
                                 'minute': minute_goal}
                            )
                        minute_goal = self.__process_goal_minute(child.get_text(strip=True).lower())
                        if child.a:
                            if child.a['title'] == 'Autogol':
                                type_goal = 'own goal'
                            if child.a['title'] == 'Penal':
                                type_goal = 'penalty'
                count_element += 1

        if author_goal:
            goals.append(
                {'author': author_goal,
                 'type': type_goal,
                 'minute': minute_goal}
            )

        if len(goals) == num_goals:
            return goals
        else:
            raise Exception('Couldnt collect all information about goals')

    def __read_results_new_format(self, num_teams):
        num_teams = int(num_teams)
        games, fx_games = [], []
        tables = self.dom.find_all('table')
        for table in tables:
            if table.has_attr('class') and 'wikitable' in table['class']:
                continue
            game = {}
            rows = table.find_all('tr')
            header = rows[0]
            details = rows[1]
            # collect info from header
            cols_header = header.find_all('td')
            game_dt = self.__process_datetime_new_format(self.__clean_text_tag(cols_header[0]))
            game['datetime'] = self.py_timezone.localize(game_dt)
            game['home_team'] = cols_header[1].get_text(strip=True).lower()
            result = cols_header[2].span.b.get_text(strip=True).lower()
            arr_result = result.split(':')
            game['result'] = {'home_team': {'goals': int(arr_result[0])},
                              'away_team': {'goals': int(arr_result[1])}}
            game['awayteam'] = cols_header[3].get_text(strip=True).lower()
            if game['home_team'] == 'sportivo trinidense' and game['awayteam'] == 'independiente (cg)':
                pass
            stadium = cols_header[4].span.get_text(strip=True).lower()
            game['stadium'] = stadium.replace('estadio', '').replace(',', '').strip()
            # collect info from details
            cols_details = details.find_all('td')
            game['home_goals'] = self.__process_goal_new_format(cols_details[1], game['result']['home_team']['goals'])
            game['away_goals'] = self.__process_goal_new_format(cols_details[3], game['result']['away_team']['goals'])
            extra_info = cols_details[4].get_text(strip=True).lower()
            arr_extra_info = extra_info.split(':')
            game['referee'] = utils.to_unicode(arr_extra_info[2].strip())
            game['audience'] = self.num_pattern.sub('',arr_extra_info[1])
            fx_games.append(game)
            if len(fx_games) == (num_teams/2):
                games.append(fx_games)
                fx_games = []

        return games

    def __get_fixture_tables(self):
        tables = self.dom.find_all('table')
        game_tables = []
        for table in tables:
            if table.has_attr('width') and table['width'] == '100%':
                continue
            table_headers = table.find_all('th')
            for table_header in table_headers:
                header_content = table_header.get_text(strip=True).lower()
                if 'fecha' in header_content:
                    game_tables.append(table)
                elif 'goles' in header_content:
                    game_tables.append(table)
        return game_tables

    def __process_game_date(self, table_cell, year):
        try:
            date_info = table_cell.contents[0].lower().replace('de', '').split()
        except:
            date_info = table_cell.lower().replace('de', '').split()
        day = int(date_info[0])
        month = utils.translate_spanish_month_letter_to_number(date_info[1])
        return date(int(year), month, day).isoformat()

    def __process_stadium_cell(self, table_cell):
        try:
            stadium_tag = table_cell.a
            stadium_wikipage = stadium_tag['href']
            stadium = {'name': utils.to_unicode(stadium_tag.get_text(strip=True)),
                       'wikipage': self.prefix_url + stadium_wikipage if 'redlink' not in stadium_wikipage else ''}
        except:
            stadium = {'name': utils.to_unicode(table_cell)}
        return stadium

    def __insert_content_in_row_array(self, content, array):
        # Insert content in the first empty (None) place of the array
        array_length = len(array)
        for i in range(0, array_length):
            if array[i] is None:
                array[i] = content
                return array

    def __get_column_for_content(self, type_content, headers):
        m_h = len(headers)
        for i in range(0, m_h):
            header = headers[i]
            if header['content'] in type_content:
                return i

    def __identify_type_content(self, content, pos_std, pos_yc):
        if ' de ' in content:
            return 'dia'
        elif ':' in content:
            return 'hora'
        elif '/' in content:
            if pos_yc == 0:
                return 'tarjetas amarillas'
            else:
                return 'tarjetas rojas'
        else:
            content = content.replace('.', '')
            if content.isdigit():
                return 'asistencia o pagantes'
            else:
                if pos_std == 0:
                    return 'estadio'
                else:
                    return 'arbitro'

    def __clean_text_tag(self, tag_txt):
        if tag_txt.sup:
            tag_txt.sup.clear()
        content = utils.to_unicode(tag_txt.get_text().lower())
        content = content.replace(u'\xa0', u' ')  # Remove unicode representation of blank space (\xa0)
        if u'\u200b' in content:
            idx_square_bracket = content.find('[')
            content = content[0:idx_square_bracket]
        if u'\u200b' in content:
            content = content.replace(u'\u200b', u'')
        content = content.replace('\n', ' ')

        return content

    def __table_to_matrix(self, table):
        table_matrix = []
        # Save table header
        row_header = []
        table_headers = table.find_all('th')
        for table_header in table_headers:
            if 'fecha' in table_header.get_text(strip=True).lower():
                continue
            if 'goles' in table_header.get_text(strip=True).lower():
                continue
            if table_header.get_text(strip=True) != '':
                if table_header.sup:
                    table_header.sup.clear()
                row_header.append({
                    'content': utils.normalize_text(table_header.get_text(strip=True).lower()),
                    'repeat_for': 0
                })
            else:
                if table_header.a:
                    if 'amonestaciones' in table_header.a['title'].lower():
                        row_header.append({
                            'content': 'tarjetas amarillas',
                            'repeat_for': 0
                        })
                    if 'expulsiones' in table_header.a['title'].lower():
                        row_header.append({
                            'content': 'tarjetas rojas',
                            'repeat_for': 0
                        })
        num_col_table = len(row_header)
        table_matrix.append(row_header)
        # Save table body
        rows = table.find_all('tr')
        num_rows = len(rows)
        span_contents = []
        for i in range(2, num_rows):
            row_body = [None] * num_col_table
            columns = rows[i].find_all('td')
            num_col_row = len(columns)
            pos_std, pos_yc = 0, 0
            if num_col_row < num_col_table:
                for span_content in span_contents:
                    if i in span_content['affected_rows']:
                        row_body[span_content['col']] = span_content['content']
            for j in range(0, num_col_row):
                content = self.__clean_text_tag(columns[j])
                if columns[j].has_attr('rowspan'):
                    type_content = self.__identify_type_content(content, pos_std, pos_yc)
                    if type_content == 'tarjetas amarillas':
                        pos_yc = 1
                    if type_content == 'estadio':
                        pos_std = 1
                    span_contents.append({
                        'content': content.strip(),
                        'affected_rows': list(range(i, i+int(columns[j]['rowspan']))),
                        'col': self.__get_column_for_content(type_content, row_header)
                    })
                row_body = self.__insert_content_in_row_array(content.strip(), row_body)
            table_matrix.append(row_body)

        return table_matrix

    def __process_goal_minute(self, scorer_str):
        if '+' in scorer_str:
            arr_m = scorer_str.split('+')
            arr_m[0] = int(self.num_pattern.sub('', arr_m[0]))
            arr_m[1] = int(self.num_pattern.sub('', arr_m[1]))
            minute = str(arr_m[0] + arr_m[1])
        else:
            minute = self.num_pattern.sub('', scorer_str)

        return minute

    def __get_goal_author_game(self, raw_author_name):
        n_author_name = utils.normalize_text(raw_author_name)
        n_author_name = self.alpha_pattern.sub('', n_author_name).strip()
        return raw_author_name[0: len(n_author_name)]

    def __process_goal_scorer(self, scorer_str):
        num_goals, num_penalties = 1, 0
        goals = []

        if 'e/c)' in scorer_str or 'a.g.)' in scorer_str:
            scorer_str = scorer_str.replace('e/c)', '')
            scorer_str = scorer_str.replace('a.g.)', '')
            idx_bracket = scorer_str.find('(')
            num_ec = scorer_str[idx_bracket: len(scorer_str)]
            scorer_str = scorer_str[0:idx_bracket]
            num_ec = num_ec.replace('(', '').strip()
            num_ec = int(num_ec) if num_ec else 1
            for c_goal in range(0, num_ec):
                minute = self.__process_goal_minute(scorer_str) if "'" in scorer_str else ''
                author = self.__get_goal_author_game(scorer_str).strip()
                goal = {'author': author, 'type': 'own goal'}
                if minute:
                    goal['minute'] = minute
                goals.append(goal)
        else:
            if '(' in scorer_str:
                # means that the scorer made more than one goal
                # and/or made a penalty goal
                sc = scorer_str.split('(')
                author = sc[0].strip()
                sc = sc[1].replace(')', '')
                if ';' in sc:
                    sp_sc = sc.split(';')
                    num_goals = int(sp_sc[0])
                    if sc[1].replace('p', '').strip().isdigit():
                        num_penalties = int(sc[1].replace('p', '').strip())
                    else:
                        num_penalties = 1
                else:
                    if sc.isdigit():
                        num_goals = int(sc)
                    else:
                        if 'p' in sc or 'pen' in sc:
                            sc = sc.replace('pen', '').replace('p', '').replace('.','')
                            if sc:
                                num_penalties = num_goals = int(sc)
                            else:
                                num_penalties = num_goals = 1
                        else:
                            author += ' ({0})'.format(sc)   # assume that sc contains the nickname of the author
                for c_goal in range(0, num_goals):
                    minute = self.__process_goal_minute(author) if "'" in scorer_str else ''
                    author = self.__get_goal_author_game(scorer_str).strip()
                    goal = {'author': author}
                    if minute:
                        goal['minute'] = minute
                    if num_penalties > 0:
                        num_penalties -= 1
                        goal['type'] = 'penalty'
                    else:
                        goal['type'] = ''
                    goals.append(goal)
            else:
                if ',' in scorer_str:
                    author = self.__get_goal_author_game(scorer_str).replace('pen', '').strip()
                    fnum = re.search('\d', scorer_str)
                    if fnum:
                        goals_info = scorer_str[fnum.start():len(scorer_str)]
                        goals_arr = goals_info.split(',')
                        for goal_info in goals_arr:
                            if '(pen)' in goal_info:
                                type_goal = 'penalty'
                            else:
                                type_goal = ''
                            goal = {'author': author,'type': type_goal}
                            minute = self.__process_goal_minute(goal_info)
                            if minute:
                                goal['minute'] = minute
                            goals.append(goal)
                else:
                    minute = self.__process_goal_minute(scorer_str) if "'" in scorer_str else ''
                    author = self.__get_goal_author_game(scorer_str).strip()
                    goal = {'author': author, 'type': ''}
                    if minute:
                        goal['minute'] = minute
                    goals.append(goal)
        return goals

    def __check_name_goal_author_presence(self, str):
        n_author_name = utils.normalize_text(str).strip()
        n_author_name = self.alpha_pattern.sub('', n_author_name)
        if n_author_name:
            return True
        else:
            return False

    def __process_goal_scorers(self, scorers_str):
        scorers = []
        raw_scorers = scorers_str.split(',')
        num_scorers = len(raw_scorers)
        idx = 0
        while idx < num_scorers:
            if ' y ' in raw_scorers[idx]:
                rs = raw_scorers.pop(idx).split(' y ')
                raw_scorers.extend(rs)
                num_scorers = len(raw_scorers)
            elif ' e ' in raw_scorers[idx]:
                rs = raw_scorers.pop(idx).split(' e ')
                raw_scorers.extend(rs)
                num_scorers = len(raw_scorers)
            else:
                str_scorer = raw_scorers[idx].strip()
                if self.__check_name_goal_author_presence(str_scorer):
                    scorers.extend(self.__process_goal_scorer(str_scorer))
                else:
                    goal_author = self.__get_goal_author_game(raw_scorers[idx-1]).strip()
                    raw_scorers[idx] = goal_author + ' ' + str_scorer
                    scorers.extend(self.__process_goal_scorer(raw_scorers[idx]))
                idx += 1

        return scorers

    def __process_game_goals(self, game_goals_str, game_result):
        goal_str = game_goals_str.split(':')
        home_goals, away_goals = [], []
        ok_home_goals, ok_away_goals = False, False
        if '-' in goal_str[1]:
            home_goal_scorers_str = goal_str[1].split('-')[0].strip()
            away_goal_scorers_str = goal_str[1].split('-')[1].strip()
            home_goals = self.__process_goal_scorers(home_goal_scorers_str)
            away_goals = self.__process_goal_scorers(away_goal_scorers_str)
        else:
            if game_result['home_team']['goals'] > 0:
                home_goals = self.__process_goal_scorers(goal_str[1])
            else:
                away_goals = self.__process_goal_scorers(goal_str[1])
        if len(home_goals) == game_result['home_team']['goals']:
            ok_home_goals = True
        if len(away_goals) == game_result['away_team']['goals']:
            ok_away_goals = True
        if ok_home_goals and ok_away_goals:
            return {'home_goals': home_goals, 'away_goals': away_goals}
        else:
            if not ok_home_goals:
                raise Exception('Couldnt collect all information of home goals')
            if not ok_away_goals:
                raise Exception('Couldnt collect all information of away goals')

    def __process_fixture_table(self, fixture_table, year):
        game_results = []
        matrix_table = self.__table_to_matrix(fixture_table)
        num_rows = len(matrix_table)
        headers = matrix_table[0]
        for i in range(1, num_rows):
            row_num_cols = len(matrix_table[i])
            if None in matrix_table[i]:
                # process goal row
                for j in range(0, row_num_cols):
                    if matrix_table[i][j] and 'gol' in matrix_table[i][j]:
                        n = len(game_results)
                        game_results[n-1]['goals'] = self.__process_game_goals(matrix_table[i][j],
                                                                               game_results[n-1]['result'])
            else:
                game = {}
                for j in range(0, row_num_cols):
                    if 'equipo local' in headers[j]['content']:
                        game['home_team'] = {'name': matrix_table[i][j]}
                    if 'resultado' in headers[j]['content']:
                        resultado = matrix_table[i][j].split('-')
                        game['result'] = {'home_team': {'goals': int(resultado[0])},
                                          'away_team': {'goals': int(resultado[1])}}
                    if 'equipo visitante' in headers[j]['content']:
                        game['away_team'] = {'name': matrix_table[i][j]}
                    if 'dia' in headers[j]['content']:
                        game['date'] = self.__process_game_date(matrix_table[i][j], year)
                    if 'hora' in headers[j]['content']:
                        game_time = datetime.strptime(matrix_table[i][j], '%H:%M')
                        game_date = datetime.strptime(game['date'], '%Y-%m-%d')
                        game['datetime'] = datetime(game_date.year,game_date.month,game_date.day,
                                                    game_time.hour,game_time.minute,game_time.second)
                        # localize game time to paraguayan timezone
                        game['datetime'] = self.py_timezone.localize(game['datetime'])
                    if 'estadio' in headers[j]['content']:
                        game['stadium'] = self.__process_stadium_cell(matrix_table[i][j])
                    if 'asistencia' in headers[j]['content']:
                        game['audience'] = matrix_table[i][j]
                    if 'arbitro' in headers[j]['content']:
                        game['referee'] = matrix_table[i][j]
                    if 'tarjetas amarillas' in headers[j]['content']:
                        yellow_cards = matrix_table[i][j].split('/')
                        game['home_team']['yellow_cards'] = yellow_cards[0].strip()
                        game['away_team']['yellow_cards'] = yellow_cards[1].strip()
                    if 'tarjetas rojas' in headers[j]['content']:
                        red_cards = matrix_table[i][j].split('/')
                        game['home_team']['red_cards'] = red_cards[0].strip()
                        game['away_team']['red_cards'] = red_cards[1].strip()
                game_results.append(game)

        return game_results


class ParaguayanTournamentScraper:
    url = ''
    dom = None
    prefix_url = 'https://es.wikipedia.org'

    def __init__(self, url):
        self.url = url

    def __update_teams_info(self, teams, teams_extra_info, update_dict=True, new_key=''):
        if teams:
            for team in teams:
                for team_extra_info in teams_extra_info:
                    if team['name'] == team_extra_info['name']:
                        if update_dict:
                            team.update(team_extra_info)
                        else:
                            team[new_key] = team_extra_info
                        break
        else:
            teams = teams_extra_info
        return teams

    def __get_info_to_collect(self, championship):
        additional_info = championship['additional_info']
        return [option.strip() for option in additional_info.split(';')]

    def collect_tournament_info(self, championship):
        ret = requests.get(self.url)
        if ret.status_code == 200:
            self.dom = BeautifulSoup(ret.text, 'html.parser')
            information_to_collect = self.__get_info_to_collect(championship)
            championship_year = str(championship['year'])
            championship_name = championship['name']
            teams = {}
            champ = {}
            if 'teams info' in information_to_collect:
                teams = self.__process_table_teams(
                    self.__get_table_teams(championship_year)
                )
            if 'season statuses' in information_to_collect:
                season_statuses = self.__process_table_season_statuses(
                    self.__get_table_season_statuses(championship_year), championship_year
                )
                teams = self.__update_teams_info(teams, season_statuses, False, 'season')
            if 'top scorers' in information_to_collect:
                champ['top_scorers'] = self.__process_table_top_scorers(
                    self.__get_championship_top_scorers()
                )
            if 'coach substitutions' in information_to_collect:
                champ['coach_substitutions'] = self.__process_table_coach_substitutions(
                    self.__get_coach_substitutions_info(championship_name, championship_year),
                    championship_year
                )
            if 'team buyers' in information_to_collect:
                team_buyers = self.__process_table_team_buyers(
                    self.__get_table_team_buyers()
                )
                teams = self.__update_teams_info(teams, team_buyers)
            if 'game top audiences' in information_to_collect:
                champ['top_audiences'] = self.__process_table_top_audience_games(
                    self.__get_info_games_large_audience()
                )
            if 'team cards' in information_to_collect:
                team_cards = self.__process_table_team_cards(
                    self.__get_table_team_cards()
                )
                teams = self.__update_teams_info(teams, team_cards)
            if 'referees' in information_to_collect:
                champ['referees'] = self.__process_table_referees(
                    self.__get_referees_info()
                )
            if 'team audiences' in information_to_collect:
                team_audiences = self.__process_table_team_audience(
                    self.__get_table_audience()
                )
                teams = self.__update_teams_info(teams, team_audiences)
            return {
                'championship': champ,
                'teams': teams
            }
        else:
            raise Exception('Request get the code ' + ret.status_code)

    def __process_team_cell(self, table_cell):
        team_tags = table_cell.find_all('a')
        team = {}
        for team_tag in team_tags:
            if team_tag.has_attr('title'):
                team_wikipage = team_tag['href']
                team['name'] = utils.to_unicode(team_tag.get_text(strip=True).lower())
                team['wikipage'] = self.prefix_url + team_wikipage if 'redlink' not in team_wikipage else ''
                break
        return team

    def __process_coach_cell(self, table_cell):
        coach_tag = table_cell.find('a')
        if coach_tag:
            coach = {'name': utils.to_unicode(coach_tag.get_text(strip=True).lower())}
            coach_wikipage = coach_tag['href']
            coach['wikipage'] = self.prefix_url + coach_wikipage if 'redlink' not in coach_wikipage else ''
        else:
            coach = {'name': utils.to_unicode(table_cell.get_text(strip=True).lower())}
        try:
            nationality = table_cell.span.img['alt'].replace('Bandera de', '').strip().lower()
            coach['country'] = nationality
        except:
            pass
        return coach

    def __process_coach_substitution_date_cell(self, table_cell, year):
        date_info = table_cell.contents[0].lower().replace('de', '').split()
        day = int(date_info[0])
        month = utils.translate_spanish_month_letter_to_number(date_info[1])
        return date(int(year), month, day).isoformat()

    def __process_date_cell(self, table_cell):
        date_links = table_cell.find_all('a')
        day_month = date_links[0].get_text(strip=True).lower().replace('de', '').split()
        day = int(day_month[0])
        month = utils.translate_spanish_month_letter_to_number(day_month[1])
        year = int(date_links[1].get_text(strip=True).lower())
        return date(year, month, day).isoformat()

    def __process_stadium_cell(self, table_cell):
        stadium_tag = table_cell.find('a')
        if stadium_tag:
            stadium_wikipage = stadium_tag['href']
            stadium = {'name': utils.to_unicode(stadium_tag.get_text(strip=True).lower()),
                       'wikipage': self.prefix_url + stadium_wikipage if 'redlink' not in stadium_wikipage else ''}
        else:
            stadium = {'name': utils.to_unicode(table_cell.get_text(strip=True).lower())}
        return stadium

    def __process_city_cell(self, table_cell):
        city_tag = table_cell.find('a')
        if city_tag:
            city_wikipage = city_tag['href']
            city = {'name': utils.to_unicode(city_tag.get_text(strip=True).lower()),
                    'wikipage': self.prefix_url + city_wikipage if 'redlink' not in city_wikipage else ''}
        else:
            city = {'name': utils.to_unicode(table_cell.get_text(strip=True).lower())}
        return city

    def __process_table_teams(self, table):
        teams = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            team = {}
            for j in range(0, num_cols):
                if 'equipo' in header[j]:
                    team.update(self.__process_team_cell(table_columns[j]))
                if 'ciudad' in header[j]:
                    team['city'] = self.__process_city_cell(table_columns[j])
                if 'estadio' in header[j]:
                    team['stadium'] = self.__process_stadium_cell(table_columns[j])
                if 'capacidad' in header[j]:
                    team['stadium']['capacity'] = table_columns[j].get_text(strip=True).replace('.', '')
                if 'fundacion' in header[j]:
                    team['foundation'] = self.__process_date_cell(table_columns[j])
                if 'entrenador' in header[j]:
                    team['coach'] = self.__process_coach_cell(table_columns[j])
                if 'indumentaria' in header[j]:
                    team['brand'] = table_columns[j].get_text(strip=True).lower()
            teams.append(team)
        return teams

    def __get_table(self, headers):
        tables = self.dom.find_all('table')
        match_tables = []
        for table in tables:
            dict_headers = {h: False for h in headers}
            table_headers = table.find_all('th')
            for table_header in table_headers:
                header_content = table_header.get_text(strip=True).lower()
                if dict_headers.get(header_content) is not None:
                    dict_headers[header_content] = True
            headers_found = [dict_headers[h] for h in dict_headers.keys()]
            if False not in headers_found:
                match_tables.append(table)
        return match_tables

    '''
       Get all information about teams
       Key words: team info
       '''
    def __get_table_teams(self, year):
        if year in ['1998', '1999', '2000', '2001', '2006','2007', '2008',
                    '2009', '2015', '2016', '2017']:
            headers = ['equipo', 'ciudad', 'estadio', 'capacidad']
        #  year in ['2010','2011', '2012', '2013', '2014']:
        else:
            headers = ['equipos', 'ciudad', 'estadio', 'capacidad']
        table_teams = self.__get_table(headers)
        if table_teams:
            return table_teams[0]
        else:
            raise Exception('Could not find table of teams')

    def __process_table_team_audience(self, table):
        team_audiences = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            team = {}
            for j in range(0, num_cols):
                if 'equipos' in header[j]:
                    team.update(self.__process_team_cell(table_columns[j]))
                if 'reacaudaci' in header[j]:
                    team['income'] = table_columns[j].get_text(strip=True).replace(' ', '')
                if 'pagantes' in header[j]:
                    team['buyers'] = table_columns[j].get_text(strip=True).replace(' ', '')
                if 'asistentes' in header[j]:
                    team['audience'] = table_columns[j].get_text(strip=True).replace(' ', '')
            team_audiences.append(team)
        return team_audiences

    '''
    Get information about total audience per team
    Key words: team audiences
    '''
    def __get_table_audience(self):
        headers = ['equipos', 'pagantes', 'asistentes']
        table_audience = self.__get_table(headers)
        if table_audience:
            return table_audience[0]
        else:
            raise Exception('Could not find table of team audiences')

    def __process_table_team_cards(self, table):
        team_cards = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            team = {}
            for j in range(0, num_cols):
                if 'equipo' in header[j]:
                    team.update(self.__process_team_cell(table_columns[j]))
                if 'ta' == header[j]:
                    team['yellow_cards'] = table_columns[j].get_text(strip=True)
                if 'rd' == header[j]:
                    team['red_cards'] = table_columns[j].get_text(strip=True)
                if 'pj' == header[j]:
                    team['games'] = table_columns[j].get_text(strip=True)
            team_cards.append(team)
        return team_cards

    '''
    Get information about total buyers per team
    Key words: team cards
    '''
    def __get_table_team_cards(self):
        headers = ['equipo', 'ta', 'tr', 'rd', 'pj']
        table_cards = self.__get_table(headers)
        if table_cards:
            return table_cards[0]
        else:
            raise Exception('Could not find table of team cards')

    def __process_table_team_buyers(self, table):
        team_buyers = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            team = {}
            for j in range(0, num_cols):
                if 'equipos' in header[j]:
                    team.update(self.__process_team_cell(table_columns[j]))
                if 'pj' == header[j]:
                    team['games'] = table_columns[j].get_text(strip=True)
                if 'as.' in header[j]:
                    team['buyers'] = table_columns[j].get_text(strip=True).replace('.', '')
            team_buyers.append(team)
        return team_buyers

    '''
    Get information about total buyers per team
    Key words: team buyers
    '''
    def __get_table_team_buyers(self):
        headers = ['equipos', 'pj', 'as.', 'pos.']
        table_buyers = self.__get_table(headers)
        if table_buyers:
            return table_buyers[0]
        else:
            raise Exception('Could not find table of team season buyers')

    def __process_team_season_final_status(self, row, year):
        if year == '1998':
            if row.has_attr('style'):
                if row['style'] == 'background:' + YELLOW_HEX:
                    return ['libertadores', 'mercosur']
            else:
                return None
        if year == '1999':
            if row.has_attr('bgcolor'):
                return ['relegation']
            else:
                return None
        if year == '2000':
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + PINK_HEX:
                    return ['relegation']
            else:
                return None
        if year in ['2001', '2003', '2004']:
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + YELLOW_HEX:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + RED_HEX:
                    return ['relegation']
            else:
                return None
        if year == '2002':
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + YELLOW_HEX or \
                   row['style'].lower() == 'background:' + BLUE_HEX:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + GREEN_HEX:
                    return ['sub relegation']
                if row['style'].lower() == 'background:' + LIGHT_GREEN_HEX:
                    return ['relegation']
            else:
                return None
        if year == '2005':
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + YELLOW_HEX:
                    return ['libertadores', 'sudamericana']
                if row['style'].lower() == 'background:' + BLUE_HEX:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + LIGHT_GREEN_HEX:
                    return ['sudamericana']
                if row['style'].lower() == 'background:' + RED_HEX:
                    return ['relegation']
            else:
                return None
        if 2005 < int(year) < 2016:
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + LIGHT_YELLOW_HEX:
                    return ['libertadores', 'sudamericana']
                if row['style'].lower() == 'background:' + GREEN_HEX:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + LIGHT_BLUE_HEX:
                    return ['sudamericana']
            else:
                return None
        if int(year) == 2016:
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + LIGHT_YELLOW_HEX or \
                   row['style'].lower() == 'background:' + DARK_GREEN_HEX or \
                   row['style'].lower() == 'background:' + GREEN_HEX2:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + LIGHT_BLUE_HEX:
                    return ['sudamericana']
            else:
                return None
        if int(year) == 2017:
            if row.has_attr('style'):
                if row['style'].lower() == 'background:' + DARK_YELLOW_HEX or \
                   row['style'].lower() == 'background:' + ORANGE_HEX or \
                   row['style'].lower() == 'background:' + LIGHT_GREEN_HEX2 or \
                   row['style'].lower() == 'background:' + LIGHT_YELLOW_HEX:
                    return ['libertadores']
                if row['style'].lower() == 'background:' + LIGHT_BLUE_HEX2:
                    return ['sudamericana']
            else:
                return None

    def __process_table_season_statuses(self, table, year):
        team_season = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            team = {}
            for j in range(0, num_cols):
                if 'equipo' in header[j] or 'equipos' in header[j]:
                    team.update(self.__process_team_cell(table_columns[j]))
                if 'pts' in header[j]:
                    team['points'] = table_columns[j].get_text(strip=True)
                if 'pj' == header[j]:
                    team['games'] = table_columns[j].get_text(strip=True)
                if 'pg' == header[j] or 'g' == header[j]:
                    team['won'] = table_columns[j].get_text(strip=True)
                if 'pe' == header[j] or 'e' == header[j]:
                    team['drew'] = table_columns[j].get_text(strip=True)
                if 'pp' == header[j] or 'p' == header[j]:
                    team['lost'] = table_columns[j].get_text(strip=True)
                if 'gf' == header[j]:
                    team['gf'] = table_columns[j].get_text(strip=True)
                if 'gc' == header[j]:
                    team['gc'] = table_columns[j].get_text(strip=True)
                if 'dif' in header[j]:
                    team['goals_difference'] = table_columns[j].get_text(strip=True)
            team['international_status'] = self.__process_team_season_final_status(table_rows[i], year)
            team['position'] = i
            team_season.append(team)
        return team_season

    '''
    Get information about teams' season final status
    Key words: season statuses
    '''
    def __get_table_season_statuses(self, year):
        if year in ['1998', '2000', '2001', '2002', '2003']:
            headers = ['pos', 'equipo', 'pts', 'pj', 'g', 'e', 'p', 'gf', 'gc', 'dif']
        elif year in ['2006', '2009', '2011', '2012', '2013', '2014']:
            headers = ['pos.', 'equipos', 'pts.', 'pj', 'pg', 'pe', 'pp', 'gf', 'gc', 'dif.']
        elif year in ['2004', '2005']:
            headers = ['equipo', 'pts', 'pj', 'g', 'e', 'p', 'gf', 'gc', 'dif']
        elif year in ['1999', '2010']:
            headers = ['pos.', 'equipos', 'pj', 'pg', 'pe', 'pp', 'gf', 'gc', 'dif.', 'pts.']
        # year in ['2007', '2008', '2015', '2016']
        else:
            headers = ['pos.', 'equipo', 'pj', 'pg', 'pe', 'pp', 'gf', 'gc', 'dif.', 'pts.']
        tables_season = self.__get_table(headers)
        table_season = None
        for table in tables_season:
            # get all rows
            table_rows = table.find_all('tr')
            # get first team
            first_team = table_rows[1]   # first row is the header
            pj_idx = headers.index('pj')
            print(pj_idx)
            first_team_pj = int(first_team.find_all('td')[pj_idx].get_text(strip=True))
            # pj should be equal to the total games in the season
            if int(year) == 1998:
                found_table_season = first_team_pj == 22
            elif int(year) == 1999:
                found_table_season = first_team_pj == 20
            elif int(year) == 2001:
                found_table_season = first_team_pj == 18
            elif int(year) == 2000 or \
                 2002 <= int(year) <= 2003:
                found_table_season = first_team_pj == 27
            elif 2004 <= int(year) <= 2005:
                found_table_season = first_team_pj == 36
            elif int(year) == 2006:
                found_table_season = first_team_pj == 40
            else:
                found_table_season = first_team_pj == 44
            if found_table_season:
                table_season = table
                break
        if table_season:
            return table_season
        else:
            raise Exception('Could not find table season')

    def __process_country_flag_cell(self, table_cell):
        country_flag = table_cell.span.img
        return utils.to_unicode(country_flag['title'].replace('Bandera de', '').strip().lower())

    def __process_player_cell(self, table_cell):
        player_tag = table_cell.find('a')
        player_wikipage = player_tag['href']
        player = {'name': utils.to_unicode(player_tag.get_text(strip=True).lower()),
                  'wikipage': self.prefix_url + player_wikipage if 'redlink' not in player_wikipage else ''}
        return player

    def __process_table_top_scorers(self, table):
        top_scorers = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            top_scorer = {}
            for j in range(0, num_cols):
                if 'pais' in header[j]:
                    top_scorer['country'] = self.__process_country_flag_cell(table_columns[j])
                if 'jugador' in header[j]:
                    top_scorer['scorer'] = self.__process_player_cell(table_columns[j])
                if 'equipo' in header[j]:
                    top_scorer['team'] = self.__process_team_cell(table_columns[j])
                if 'goles' in header[j]:
                    top_scorer['goals'] = table_columns[j].get_text(strip=True)
            top_scorers.append(top_scorer)
        return top_scorers

    '''
    Get information about the championship's top scorers
    Key words: top scorers
    '''
    def __get_championship_top_scorers(self):
        headers = ['jugador', 'equipo', 'goles']
        table_top_scorers = self.__get_table(headers)
        if table_top_scorers:
            return table_top_scorers[0]
        else:
            raise Exception('Could not find table of top scorers')

    def __process_table_coach_substitutions(self, table, year):
        coach_substitutions = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            substitution = {}
            for j in range(0, num_cols):
                if 'equipos' in header[j]:
                    substitution['team'] = self.__process_team_cell(table_columns[j])
                if 'ste' in header[j] or 'saliente' in header[j]:
                    substitution['coach_out'] = self.__process_coach_cell(table_columns[j])
                if 'cese' in header[j]:
                    substitution['date_out'] = self.__process_coach_substitution_date_cell(table_columns[j], year)
                if 'ete' in header[j] or 'entrante' in header[j]:
                    substitution['coach_in'] = self.__process_coach_cell(table_columns[j])
                if 'designaci' in header[j]:
                    substitution['date_in'] = self.__process_coach_substitution_date_cell(table_columns[j], year)
                if 'fechas dirigidas' in header[j]:
                    substitution['coach_out']['games'] = table_columns[j].get_text(strip=True)
            coach_substitutions.append(substitution)
        return coach_substitutions

    '''
    Get information about coach changes during the 
    tournament
    Key words: coach substitutions
    '''
    def __get_coach_substitutions_info(self, championship_name, year):
        if int(year) < 2016 or \
           (int(year) == 2016 and 'apertura' in championship_name):
            headers = ['equipos', 'dt. ste.', 'cese', 'dt. ete.']
        else:
            headers = ['equipos', 'dt. saliente', 'cese', 'dt. entrante', 'fechas dirigidas']
        table_coaches = self.__get_table(headers)
        if table_coaches:
            return table_coaches[0]
        else:
            raise Exception('Could not find table of coach replacements')

    def __process_table_top_audience_games(self, table):
        top_audience_games = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            top_audience_game = {}
            for j in range(0, num_cols):
                if 'partido' in header[j]:
                    teams = table_columns[j].get_text(strip=True).split('-')
                    top_audience_game['home_team'] = utils.to_unicode(teams[0].lower())
                    top_audience_game['away_team'] = utils.to_unicode(teams[1].lower())
                if 'asistentes' in header[j]:
                    top_audience_game['audience'] = table_columns[j].get_text(strip=True).replace('.', '')
                if 'estadio' in header[j]:
                    top_audience_game['stadium'] = self.__process_stadium_cell(table_columns[j])
                if 'fecha' in header[j]:
                    top_audience_game['game'] =  table_columns[j].get_text(strip=True)
            top_audience_games.append(top_audience_game)
        return top_audience_games

    '''
    Get information about games with the largest audience
    in the tournament
    Key words: games top audiences
    '''
    def __get_info_games_large_audience(self):
        headers = ['pos.', 'partido', 'asistentes', 'estadio', 'fecha']
        table_top_audiences = self.__get_table(headers)
        if table_top_audiences:
            return table_top_audiences[0]
        else:
            raise Exception('Could not find table of games with top audiences')

    def __process_table_referees(self, table):
        referees = []
        header = []
        # Process Table Headers
        table_headers = table.find_all('th')
        for table_header in table_headers:
            header.append(table_header.get_text(strip=True).lower())
        # Process Table Rows
        table_rows = table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(1, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            referee = {}
            for j in range(0, num_cols):
                if 'rbitro' in header[j]:
                    referee['name'] = table_columns[j].get_text(strip=True).lower()
                if 'ta' == header[j]:
                    referee['yellow_cards'] = table_columns[j].get_text(strip=True)
                if 'tr' == header[j]:
                    referee['red_cards'] = table_columns[j].get_text(strip=True)
                if 'pd' == header[j]:
                    referee['games'] = table_columns[j].get_text(strip=True)
            referees.append(referee)
        return referees

    '''
    Get information about referees
    '''
    def __get_referees_info(self):
        headers = ['ta', 'tr', 'pd']
        table_referees = self.__get_table(headers)
        if table_referees:
            return table_referees[0]
        else:
            raise Exception('Could not find table of referees')


# if __name__ == '__main__':
#     championship = utils.csv_to_dict('../data/campeonatos.csv')
#     championship_test = championship[58]
#     ws = ParaguayanChampionshipResultsScraper(
#         url=championship_test['results']
#     )
#     ret = ws.collect_championship_results(championship_test)
#     pass