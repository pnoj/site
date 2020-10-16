# Generated by Django 3.0.8 on 2020-09-09 16:33

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0030_delete_sidebaritem'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='payment_pointer',
            field=models.CharField(blank=True, max_length=300, validators=[django.core.validators.RegexValidator(message='Enter a payment pointer', regex='\\$.*\\.(?:.*)+?(?:/.*)?')]),
        ),
    ]