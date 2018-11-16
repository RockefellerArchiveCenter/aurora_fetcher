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
    PROCESS_STATUS_CHOICES = (
        (10, 'Transfer saved'),
        (20, 'Accession record created'),
        (30, 'Grouping component created'),
        (40, 'Transfer component created'),
        (50, 'Digital object created'),
    )
    process_status = models.CharField(max_length=50, choices=PROCESS_STATUS_CHOICES)
    transfer_data = JSONField(null=True, blank=True)
    accession_data = JSONField(null=True, blank=True)

    def __str__(self):
        return '{} {}'.format(self.package_type, self.identifier)

    def get_use_statement(self):
        return 'master' if (self.package_type == 'aip') else 'service-edited'
