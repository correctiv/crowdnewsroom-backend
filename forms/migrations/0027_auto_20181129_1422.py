# Generated by Django 2.0.9 on 2018-11-29 14:22

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0026_auto_20181018_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forminstance',
            name='priority_fields',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='forminstance',
            name='ui_schema_json',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='forminstancetemplate',
            name='priority_fields',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='forminstancetemplate',
            name='ui_schema_json',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict),
        ),
    ]
