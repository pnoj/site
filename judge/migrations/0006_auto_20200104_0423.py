# Generated by Django 3.0.1 on 2020-01-04 04:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0005_auto_20200104_0406'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='num_solved_problems',
            new_name='num_problems_solved',
        ),
        migrations.AlterField(
            model_name='user',
            name='organizations',
            field=models.ManyToManyField(blank=True, to='judge.Organization'),
        ),
    ]
