from django.contrib.postgres.fields import JSONField
from django.db import models


class Transfer(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    fedora_uri = models.CharField(max_length=512)
    internal_sender_identifier = models.CharField(max_length=256)
    PACKAGE_TYPE_CHOICES = (
        ('aip', 'AIP'),
        ('dip', 'DIP')
    )
    package_type = models.CharField(max_length=10, choices=PACKAGE_TYPE_CHOICES)
    transfer_data = JSONField()
    accession_data = JSONField()

    def __str__(self):
        return '{} {}'.format(self.package_type, self.internal_sender_identifier)


class Identifier(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    identifier = models.CharField(max_length=200)
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name='identifier')

    def __str__(self):
        return "{}".format(self.identifier)
