# Generated by Django 3.0.1 on 2020-01-18 23:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0011_auto_20200105_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='language',
            field=models.CharField(choices=[('py3', 'Python3'), ('java8', 'Java 8'), ('c++17', 'C++17')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='main_language',
            field=models.CharField(choices=[('py3', 'Python3'), ('java8', 'Java 8'), ('c++17', 'C++17')], default='py3', max_length=10),
        ),
    ]
