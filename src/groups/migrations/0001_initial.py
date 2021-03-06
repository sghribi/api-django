# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-09 13:46
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_countries.fields
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('is_referent', models.BooleanField(default=False, verbose_name='membre référent')),
                ('is_manager', models.BooleanField(default=False, verbose_name='gestionnaire')),
                ('person', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='people.Person')),
            ],
            options={
                'verbose_name': 'adhésion',
                'verbose_name_plural': 'adhésions',
                'permissions': (('view_membership', 'Peut afficher les adhésions'),),
            },
        ),
        migrations.CreateModel(
            name='SupportGroup',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, help_text="UUID interne à l'API pour identifier la ressource", primary_key=True, serialize=False, verbose_name='UUID')),
                ('nb_id', models.IntegerField(blank=True, help_text="L'identifiant de la ressource correspondante sur NationBuilder, si importé.", null=True, unique=True, verbose_name='ID sur NationBuilder')),
                ('coordinates', django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name='coordonnées')),
                ('location_name', models.CharField(blank=True, max_length=255, verbose_name='nom du lieu')),
                ('location_address', models.CharField(blank=True, max_length=255, verbose_name='adresse complète')),
                ('location_address1', models.CharField(blank=True, max_length=100, verbose_name='adresse (1ère ligne)')),
                ('location_address2', models.CharField(blank=True, max_length=100, verbose_name='adresse (2ème ligne)')),
                ('location_city', models.CharField(blank=True, max_length=100, verbose_name='ville')),
                ('location_zip', models.CharField(blank=True, max_length=20, verbose_name='code postal')),
                ('location_state', models.CharField(blank=True, max_length=40, verbose_name='état')),
                ('location_country', django_countries.fields.CountryField(blank=True, max_length=2, verbose_name='pays')),
                ('contact_name', models.CharField(blank=True, max_length=255, verbose_name='nom du contact')),
                ('contact_email', models.EmailField(blank=True, max_length=254, verbose_name='adresse email du contact')),
                ('contact_phone', models.CharField(blank=True, max_length=30, verbose_name='numéro de téléphone du contact')),
                ('name', models.CharField(help_text="Le nom du groupe d'action", max_length=255, verbose_name='nom')),
                ('description', models.TextField(blank=True, help_text="Une description du groupe d'action, en MarkDown", verbose_name='description')),
                ('nb_path', models.CharField(blank=True, max_length=255, verbose_name='NationBuilder path')),
                ('members', models.ManyToManyField(blank=True, related_name='supportgroups', through='groups.Membership', to='people.Person')),
            ],
            options={
                'verbose_name': "groupe d'action",
                'verbose_name_plural': "groupes d'appui",
                'ordering': ('-created',),
            },
        ),
        migrations.CreateModel(
            name='SupportGroupTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=50, unique=True, verbose_name='nom')),
                ('description', models.TextField(blank=True, verbose_name='description')),
            ],
            options={
                'verbose_name': 'tag',
            },
        ),
        migrations.AddField(
            model_name='supportgroup',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='events', to='groups.SupportGroupTag'),
        ),
        migrations.AddField(
            model_name='membership',
            name='supportgroup',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='groups.SupportGroup'),
        ),
        migrations.AddIndex(
            model_name='supportgroup',
            index=models.Index(fields=['nb_path'], name='groups_supp_nb_path_0a4cde_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='membership',
            unique_together=set([('supportgroup', 'person')]),
        ),
    ]
