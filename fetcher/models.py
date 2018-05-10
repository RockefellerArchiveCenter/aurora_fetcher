from django.contrib.postgres.fields import JSONField
from django.db import models


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
        # fetch and save updated data for an object
        pass
