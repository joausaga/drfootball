# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-09-13 14:00
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('defense', '0019_auto_20170911_0004'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tournament',
            name='champion_of_season',
        ),
    ]
