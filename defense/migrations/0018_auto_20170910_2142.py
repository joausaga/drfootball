# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-09-10 21:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('defense', '0017_auto_20170910_2139'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tournamentteam',
            name='source',
        ),
        migrations.AddField(
            model_name='tournamentteam',
            name='source',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='defense.Source'),
        ),
    ]