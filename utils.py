__author__ = 'jorgesaldivar'

import unicodedata


def to_unicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def translate_spanish_month_letter_to_number(month_letter):
    months = ['enero', 'febrero', 'marzo', 'abril', 'mayo',
              'junio', 'julio', 'agosto', 'septiembre',
              'octubre', 'noviembre', 'diciembre']
    for idx in range(0, 12):
        if months[idx] == month_letter:
            return idx + 1

def normalize_text(text):
    return unicodedata.normalize('NFD', to_unicode(text)).encode('ascii', 'ignore')