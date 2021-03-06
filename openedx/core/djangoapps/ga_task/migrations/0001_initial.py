# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('task_type', models.CharField(max_length=50, db_index=True)),
                ('task_key', models.CharField(max_length=255, db_index=True)),
                ('task_input', models.CharField(max_length=255)),
                ('task_id', models.CharField(max_length=255, db_index=True)),
                ('task_state', models.CharField(max_length=50, db_index=True)),
                ('task_output', models.CharField(max_length=1024, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('subtasks', models.TextField(blank=True)),
                ('requester', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
