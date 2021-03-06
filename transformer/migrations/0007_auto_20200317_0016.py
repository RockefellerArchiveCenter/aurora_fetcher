# Generated by Django 2.2.10 on 2020-03-17 00:16

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transformer', '0006_package_origin'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='bag_identifier',
            field=models.CharField(default=1, max_length=255, unique=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='package',
            name='bag_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='package',
            name='data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='package',
            name='type',
            field=models.CharField(blank=True, choices=[('aip', 'Archival Information Package'), ('dip', 'Dissemination Information Package')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='package',
            name='process_status',
            field=models.IntegerField(),
        ),
    ]
