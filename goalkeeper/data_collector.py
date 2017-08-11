# -*- coding: utf-8 -*-s

__author__ = 'jorgesaldivar'


import csv, parser_rsssf


def read_championships_file(fname):
    championships = []

    with open(fname, 'r') as csv_file:
        championships_reader = csv.DictReader(csv_file, delimiter=',')
        for championship in championships_reader:
            championships.append(championship)
    return championships


if __name__ == '__main__':
    dict_championships = []
    meta_championships = read_championships_file('../data/campeonatos.csv')
    for meta_championship in meta_championships:
        if int(meta_championship['year']) <= 2007:
            print('Championship %s', meta_championship['name'])
            dict_championships.append(parser_rsssf.get_data(meta_championship))
        else:
            print('here')
    print ('Finished!')