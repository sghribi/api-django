# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-31 12:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_auto_20170505_1505'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scope',
            name='label',
            field=models.CharField(max_length=50, unique=True, verbose_name='nom'),
        ),
    ]