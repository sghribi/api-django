# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-09-15 10:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0002_auto_20170615_0849'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportgroup',
            name='published',
            field=models.BooleanField(default=True, help_text='Le groupe doit-il être visible publiquement.', verbose_name='publié'),
        ),
    ]