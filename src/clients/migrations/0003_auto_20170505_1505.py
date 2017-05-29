# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-05 15:05
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0002_client_oauth_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Une adresse email de contact pour ce client.', max_length=254, verbose_name='email de contact'),
        ),
        migrations.AlterField(
            model_name='client',
            name='uris',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=150), blank=True, default=list, help_text="La liste des URIs auxquelles le serveur d'authentification acceptera de rediriger les utilisateurs pendant la procédure OAuth.", size=4, verbose_name='URIs de redirection OAuth'),
        ),
    ]