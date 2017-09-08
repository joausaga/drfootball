__author__ = 'jorgesaldivar'

import unicodedata, csv


def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def translate_spanish_month_letter_to_number(month_letter):
    months = {'enero' : 1, 'febrero' : 2,
              'marzo': 3, 'abril': 4,
              'mayo': 5, 'junio': 6,
              'julio': 7, 'agosto': 8,
              'septiembre': 9, 'setiembre': 9,
              'octubre': 10, 'noviembre': 11,
              'diciembre': 12}
    for month_name, month_number in months.items():
        if month_name == month_letter:
            return month_number


def normalize_text(text):
    return unicodedata.normalize('NFD', to_unicode(text)).encode('ascii', 'ignore')


def csv_to_dict(csv_file):
    with open(csv_file, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        csv_dict = list(csv_reader)

    return csv_dict