# Generated by Django 5.1a1 on 2024-10-06 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheets', '0009_remove_teamlog_change_timestamp_teamlog_method_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamlog',
            name='new_value',
            field=models.JSONField(),
        ),
        migrations.AlterField(
            model_name='teamlog',
            name='previous_value',
            field=models.JSONField(),
        ),
    ]
