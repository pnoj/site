# Generated by Django 3.0.1 on 2020-02-14 20:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0014_auto_20200214_1815'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='num_problems_solved',
        ),
        migrations.RemoveField(
            model_name='user',
            name='points',
        ),
    ]