# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-09-27 14:12
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.management import create_permissions


def add_view_hidden_event_permission_to_worker(apps, schema):
    # make sure permissions have been created (they are only created in post_migrate phase usually!)
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    workers = Group.objects.get(name='workers')
    group_perm = Permission.objects.get(codename='view_hidden_supportgroup')
    event_perm = Permission.objects.get(codename='view_hidden_event')

    if not workers.permissions.filter(pk=group_perm.pk).exists():
        workers.permissions.add(group_perm)

    if not workers.permissions.filter(pk=event_perm.pk).exists():
        workers.permissions.add(event_perm)


def remove_view_hidden_event_permission_from_worker(apps, schema):
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    workers = Group.objects.get(name='workers')
    group_perm = Permission.objects.get(codename='view_hidden_supportgroup')
    event_perm = Permission.objects.get(codename='view_hidden_event')

    if workers.permissions.filter(pk=event_perm.pk).exists():
        workers.permissions.remove(event_perm)

    if not workers.permissions.filter(pk=group_perm.pk).exists():
        workers.permissions.add(group_perm)


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0002_create_basic_groups'),
        ('events', '0006_auto_20170915_1510'),
        ('groups', '0004_auto_20170915_1458')
    ]

    operations = [
        migrations.RunPython(add_view_hidden_event_permission_to_worker,
                             remove_view_hidden_event_permission_from_worker)
    ]
