# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 16:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('defense', '0005_auto_20170616_1600'),
    ]

    operations = [
        migrations.RenameField(
            model_name='team',
            old_name='championships',
            new_name='international_championships',
        ),
        migrations.RenameField(
            model_name='team',
            old_name='runnerups',
            new_name='international_runnerups',
        ),
        migrations.AddField(
            model_name='team',
            name='local_championships',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='team',
            name='local_runnerups',
            field=models.IntegerField(default=0),
        ),
    ]
