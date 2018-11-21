from django.contrib.postgres.fields import JSONField
from django.db import models


class Package(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    fedora_uri = models.CharField(max_length=512)
    identifier = models.CharField(max_length=256)
    PACKAGE_TYPE_CHOICES = (
        ('aip', 'AIP'),
        ('dip', 'DIP')
    )
    package_type = models.CharField(max_length=10, choices=PACKAGE_TYPE_CHOICES)
    SAVED = 10
    ACCESSION_CREATED = 20
    GROUPING_COMPONENT_CREATED = 30
    TRANSFER_COMPONENT_CREATED = 40
    DIGITAL_OBJECT_CREATED = 50
    UPDATE_SENT = 60
    PROCESS_STATUS_CHOICES = (
        (SAVED, 'Transfer saved'),
        (ACCESSION_CREATED, 'Accession record created'),
        (GROUPING_COMPONENT_CREATED, 'Grouping component created'),
        (TRANSFER_COMPONENT_CREATED, 'Transfer component created'),
        (DIGITAL_OBJECT_CREATED, 'Digital object created'),
        (UPDATE_SENT, 'Updated data sent to Aurora')
    )
    process_status = models.CharField(max_length=50, choices=PROCESS_STATUS_CHOICES)
    transfer_data = JSONField(null=True, blank=True)
    accession_data = JSONField(null=True, blank=True)

    def __str__(self):
        return '{} {}'.format(self.package_type, self.identifier)

    def get_use_statement(self):
        return 'master' if (self.package_type == 'aip') else 'service-edited'
