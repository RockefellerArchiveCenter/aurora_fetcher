from asterism.models import BasePackage
from django.db import models


class Package(BasePackage):
    BasePackage._meta.get_field("bag_identifier")._unique = False
    fedora_uri = models.CharField(max_length=512)
    SAVED = 10
    ACCESSION_CREATED = 20
    GROUPING_COMPONENT_CREATED = 30
    TRANSFER_COMPONENT_CREATED = 40
    DIGITAL_OBJECT_CREATED = 50
    UPDATE_SENT = 60
    ACCESSION_UPDATE_SENT = 70
    PROCESS_STATUS_CHOICES = (
        (SAVED, 'Transfer saved'),
        (ACCESSION_CREATED, 'Accession record created'),
        (GROUPING_COMPONENT_CREATED, 'Grouping component created'),
        (TRANSFER_COMPONENT_CREATED, 'Transfer component created'),
        (DIGITAL_OBJECT_CREATED, 'Digital object created'),
        (UPDATE_SENT, 'Updated transfer data sent to Aurora'),
        (ACCESSION_UPDATE_SENT, 'Updated Accession data sent to Aurora')
    )
    accession_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return '{} {}'.format(self.type, self.bag_identifier)

    @property
    def use_statement(self):
        return 'master' if (self.type == 'aip') else 'service-edited'
