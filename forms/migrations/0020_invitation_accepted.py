# Generated by Django 2.0.1 on 2018-07-12 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0019_auto_20180712_0743'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='accepted',
            field=models.NullBooleanField(),
        ),
    ]