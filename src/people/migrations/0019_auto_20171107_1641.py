# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-11-07 15:41
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0018_person_form'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='meta',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, verbose_name='Autres données'),
        ),
    ]
