# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-12-05 11:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0013_change_description_help_text'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='supportgroup',
            options={'ordering': ('-created',), 'permissions': (('view_hidden_supportgroup', 'Peut afficher les groupes non publiés'),), 'verbose_name': "groupe d'action", 'verbose_name_plural': "groupes d'action"},
        ),
    ]
