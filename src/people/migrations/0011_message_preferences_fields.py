# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-09-27 18:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0010_person_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='event_notifications',
            field=models.BooleanField(default=True, help_text='Vous recevrez des messages quand les informations des évènements auxquels vous souhaitez participer sont mis à jour ou annulés.', verbose_name='Recevoir les notifications des événements'),
        ),
        migrations.AddField(
            model_name='person',
            name='group_notifications',
            field=models.BooleanField(default=True, help_text='Vous recevrez des messages quand les informations du groupe change, ou quand le groupe organise des événements.', verbose_name='Recevoir les notifications de mes groupes'),
        ),
        migrations.AlterField(
            model_name='person',
            name='subscribed',
            field=models.BooleanField(default=True, help_text="Vous recevrez les lettres de la France insoumise, notamment : les lettres d'information, les appels à volontaires, ", verbose_name="Recevoir les lettres d'information"),
        ),
    ]
