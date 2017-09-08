# -*- coding: utf-8 -*-s

__author__ = 'jorgesaldivar'


import parser_rsssf, utils


if __name__ == '__main__':
    dict_championships = []
    meta_championships = utils.csv_to_dict('../data/campeonatos.csv')
    for meta_championship in meta_championships:
        if int(meta_championship['year']) <= 2007:
            print('Championship %s', meta_championship['name'])
            dict_championships.append(parser_rsssf.get_data(meta_championship))
        else:
            print('here')
    print ('Finished!')