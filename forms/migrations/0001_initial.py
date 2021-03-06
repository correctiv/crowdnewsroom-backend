# Generated by Django 2.0.1 on 2018-03-07 13:43

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import forms.models
import forms.secrets


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', forms.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('text', models.TextField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('status', models.CharField(choices=[('D', 'Draft'), ('U', 'Unlisted'), ('P', 'Published'), ('C', 'Closed'), ('A', 'Archived')], default='D', max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='FormInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_json', django.contrib.postgres.fields.jsonb.JSONField()),
                ('ui_schema_json', django.contrib.postgres.fields.jsonb.JSONField(default={})),
                ('version', models.IntegerField(default=0)),
                ('form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.Form')),
            ],
        ),
        migrations.CreateModel(
            name='FormResponse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('json', django.contrib.postgres.fields.jsonb.JSONField()),
                ('status', models.CharField(choices=[('S', 'Submitted'), ('V', 'Verified'), ('I', 'Invalid')], default='S', max_length=1)),
                ('token', models.CharField(db_index=True, default=forms.secrets.token_urlsafe, max_length=256)),
                ('email', models.EmailField(max_length=254)),
                ('submission_date', models.DateTimeField()),
                ('form_instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.FormInstance')),
            ],
            options={
                'permissions': (('edit_response', 'Edit response'),),
            },
        ),
        migrations.CreateModel(
            name='Investigation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('cover_image', models.FileField(blank=True, default=None, null=True, upload_to='')),
                ('logo', models.FileField(blank=True, default=None, null=True, upload_to='')),
                ('short_description', models.TextField()),
                ('category', models.TextField()),
                ('research_questions', models.TextField()),
                ('status', models.CharField(choices=[('D', 'Draft'), ('P', 'Published'), ('A', 'Archived')], default='D', max_length=1)),
                ('text', models.TextField()),
                ('methodology', models.TextField()),
                ('faq', models.TextField()),
            ],
            options={
                'permissions': (('manage_investigation', 'Manage investigation')),
            },
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('logo', models.FileField(upload_to='')),
                ('url', models.TextField(max_length=1000)),
                ('investigation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.Investigation')),
            ],
        ),
        migrations.CreateModel(
            name='UserGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('O', 'Owner'), ('A', 'Admin'), ('E', 'Editor'), ('A', 'Auditor'), ('V', 'Viewer')], default='V', max_length=1)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
                ('investigation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.Investigation')),
            ],
        ),
        migrations.AddField(
            model_name='form',
            name='investigation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.Investigation'),
        ),
        migrations.AddField(
            model_name='comment',
            name='form_response',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='forms.FormResponse'),
        ),
    ]
