# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 18:01
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('defense', '0008_auto_20170616_1755'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='number',
            new_name='round',
        ),
    ]
