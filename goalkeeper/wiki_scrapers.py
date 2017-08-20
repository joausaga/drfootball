__author__ = 'jorgesaldivar'

import requests, utils, unicodedata, pytz
from bs4 import BeautifulSoup
from datetime import date, datetime
from data_collector import read_championships_file


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

    def __init__(self, url):
        self.url = url

    def collect_championship_results(self, championship):
        ret_rq = requests.get(self.url)
        if ret_rq.status_code == 200:
            self.dom = BeautifulSoup(ret_rq.text, 'html.parser')

    def __get_fixture_tables(self):
        tables = self.dom.find_all('table')
        game_tables = []
        for table in tables:
            if table.has_attr['width'] and table['width'] == '100%':
                continue
            table_headers = table.find_all('th')
            for table_header in table_headers:
                header_content = table_header.get_text(strip=True).lower()
                if 'fecha' in header_content:
                    game_tables.append(table)
        return game_tables

    def __process_game_date(self, table_cell, year):
        date_info = table_cell.contents[0].lower().replace('de', '').split()
        day = int(date_info[0])
        month = utils.translate_spanish_month_letter_to_number(date_info[1])
        return date(int(year), month, day).isoformat()

    def __process_stadium_cell(self, table_cell):
        stadium_tag = table_cell.find('a')
        if stadium_tag:
            stadium_wikipage = stadium_tag['href']
            stadium = {'name': utils.to_unicode(stadium_tag.get_text(strip=True).lower()),
                       'wikipage': self.prefix_url + stadium_wikipage if 'redlink' not in stadium_wikipage else ''}
        else:
            stadium = {'name': utils.to_unicode(table_cell.get_text(strip=True).lower())}
        return stadium

    def __process_fixture_table(self, fixture_table, year):
        game_results = []
        header = []
        # Process Table Headers
        table_headers = fixture_table.find_all('th')
        for table_header in table_headers:
            if 'fecha' in table_header:
                continue
            raw_header = table_header.get_text(strip=True).lower()
            normalized_header = unicodedata.normalize('NFD', utils.to_unicode(raw_header)).encode('ascii', 'ignore')
            header.append(normalized_header)
        # Process Table Rows
        table_rows = fixture_table.find_all('tr')
        num_rows = len(table_rows)
        for i in range(2, num_rows):
            table_columns = table_rows[i].find_all('td')
            num_cols = len(table_columns)
            game = {}
            for j in range(0, num_cols):
                if table_columns[j].has_attr('rowspan'):
                    pass
                if 'equipo local' in header[j]:
                    game['home_team'] = {'name': utils.to_unicode(table_columns[j].get_text(strip=True).lower())}
                if 'resultado' in header[j]:
                    resultado = table_columns[j].get_text(strip=True).split('-')
                    game['home_team']['goals'] = resultado[0]
                    game['away_team'] = {'goals': resultado[1]}
                if 'equipo visitante' in header[j]:
                    game['away_team']['name'] = utils.to_unicode(table_columns[j].get_text(strip=True).lower())
                if 'dia' in header[j]:
                    game['date'] = self.__process_game_date(table_columns[j], year)
                if 'hora' in header[j]:
                    game_time = datetime.strptime(table_columns[j].get_text(strip=True), '%H:%M')
                    game_date = datetime.strptime(game['date'], '%Y-%m-%d')
                    game['datetime'] = datetime(game_date.year,game_date.month,game_date.day,
                                                game_time.hour,game_time.minute,game_time.second)
                    # localize game time as paraguayan timezone
                    game['datetime'] = self.py_timezone.localize(game['datetime'])
                if 'estadio' in header[j]:
                    game['stadium'] = self.__process_stadium_cell(table_columns[j])


            game_results.append(game)
        return game_results


class ParaguayanChampionshipScraper:
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

    def collect_championship_info(self, championship):
        ret = requests.get(self.url)
        if ret.status_code == 200:
            self.dom = BeautifulSoup(ret.text, 'html.parser')
            information_to_collect = self.__get_info_to_collect(championship)
            championship_year = championship['year']
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
                'teams' : teams
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
            team_season.append(team)
        return team_season

    '''
    Get information about teams' season final status
    Key words: season statuses
    '''
    def __get_table_season_statuses(self, year):
        if year in ['1998', '2000', '2001', '2002', '2003']:
            headers = ['pos', 'equipo', 'pts', 'pj', 'g', 'e', 'p', 'gf', 'gc', 'dif']
        elif year in ['1999', '2006', '2009', '2011', '2012', '2013', '2014']:
            headers = ['pos.', 'equipos', 'pts.', 'pj', 'pg', 'pe', 'pp', 'gf', 'gc', 'dif.']
        elif year in ['2004', '2005']:
            headers = ['equipo', 'pts', 'pj', 'g', 'e', 'p', 'gf', 'gc', 'dif']
        elif year == '2010':
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
            raise Exception('Could not find table of team season buyers')

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


if __name__ == '__main__':
    championship = read_championships_file('../data/campeonatos.csv')
    championship_test = championship[2]
    ws = ParaguayanChampionshipScraper(
        url=championship_test['championship_source_url']
    )
    ret = ws.collect_championship_info(championship_test)
    pass