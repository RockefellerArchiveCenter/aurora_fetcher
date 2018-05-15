# Generated by Django 2.0 on 2018-05-15 13:28

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataObject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('type', models.CharField(choices=[('accession', 'Accession'), ('agent', 'Agent'), ('component', 'Component')], max_length=50)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Identifier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('source', models.CharField(choices=[('aurora', 'Aurora'), ('archivesspace', 'ArchivesSpace'), ('fedora', 'Fedora')], max_length=50)),
                ('identifier', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ConsumerObject',
            fields=[
                ('dataobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='transformer.DataObject')),
                ('consumer', models.CharField(choices=[('archivesspace', 'ArchivesSpace'), ('fedora', 'Fedora')], max_length=50)),
            ],
            bases=('transformer.dataobject',),
        ),
        migrations.CreateModel(
            name='SourceObject',
            fields=[
                ('dataobject_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='transformer.DataObject')),
                ('source', models.CharField(choices=[('aurora', 'Aurora')], max_length=50)),
            ],
            bases=('transformer.dataobject',),
        ),
        migrations.AddField(
            model_name='identifier',
            name='consumer_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_identifier', to='transformer.ConsumerObject'),
        ),
        migrations.AddField(
            model_name='consumerobject',
            name='source_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='source_object', to='transformer.SourceObject'),
        ),
    ]
