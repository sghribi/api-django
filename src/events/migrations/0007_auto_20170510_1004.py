# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-10 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0003_auto_20170509_0938'),
        ('events', '0006_auto_20170509_1325'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='rsvp',
            unique_together=set([('event', 'person')]),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['nb_path'], name='events_even_nb_path_2e6795_idx'),
        ),
        migrations.AddIndex(
            model_name='rsvp',
            index=models.Index(fields=['event', 'person'], name='events_rsvp_event_i_4e1eef_idx'),
        ),
    ]
