# Generated by Django 2.0.1 on 2018-05-16 07:26

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0008_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='formresponse',
            name='assignees',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
    ]
