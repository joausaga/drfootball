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


def format_text_to_save_db(text, encoding='utf-8'):
    return text.title().encode(encoding)


# Taken from
# https://stackoverflow.com/questions/1823058/how-to-print-number-with-commas-as-thousands-separators
def int_seperation_char(x, sep_char=','):
    if type(x) not in [type(0), type(0L)]:
        raise TypeError('Parameter must be an integer')
    if x < 0:
        return '-' + int_seperation_char(-x)
    result = ''
    while x >= 1000:
        x, r = divmod(x, 1000)
        result = sep_char + '%03d%s' % (r, result)
    return '%d%s' % (x, result)