# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 16:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defense', '0004_tournamentplayer'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tournament',
            name='top_scorers',
        ),
        migrations.AddField(
            model_name='tournament',
            name='scorers',
            field=models.ManyToManyField(through='defense.TournamentPlayer', to='defense.Player'),
        ),
    ]