# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-29 14:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0007_auto_20170518_1509'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='membership',
            options={'permissions': (('view_membership', 'Peut afficher les adhésions'),), 'verbose_name': 'adhésion', 'verbose_name_plural': 'adhésions'},
        ),
        migrations.AddField(
            model_name='membership',
            name='is_manager',
            field=models.BooleanField(default=False, verbose_name='gestionnaire'),
        ),
    ]
