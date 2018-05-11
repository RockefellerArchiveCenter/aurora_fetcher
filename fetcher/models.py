from django.contrib.postgres.fields import JSONField
from django.db import models

from fetcher.clients import AuroraClient


class SourceObject(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    TYPE_CHOICES = (
        ('accession', 'Accession'),
        ('agent', 'Agent'),
        ('collection', 'Collection'),
        ('component', 'Component'),
        ('term', 'Term'),
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    data = JSONField()

    def update_data(self):
        client = AuroraClient().client
        data = client.get(self.data['url'])
        self.data = data
        self.save()
