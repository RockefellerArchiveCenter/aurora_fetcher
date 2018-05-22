import logging
from structlog import wrap_logger
from uuid import uuid4

from client.clients import ArchivesSpaceClient, AuroraClient
from transformer.models import ConsumerObject, Identifier
from transformer.transformers import ArchivesSpaceDataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class AccessionRoutine:
    def __init__(self, aspace_client, aurora_client):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.aurora_client = aurora_client if aurora_client else AuroraClient()
        self.transformer = ArchivesSpaceDataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self, source_object):
        self.log.bind(request_id=str(uuid4()))
        self.source_object = source_object
        self.data = source_object.data
        if int(self.source_object.process_status) <= 10:
            if not self.create_grouping_component():
                self.log.error("Error creating grouping component", object=self.data['url'])
                return False
            self.source_object.process_status = 30
            self.source_object.save()

        if int(self.source_object.process_status) <= 30:
            # TODO: find a cleaner way to get the ArchivesSpace URI
            parent_object = ConsumerObject.objects.get(source_object=self.source_object, type='component')
            self.parent = Identifier.objects.get(consumer_object=parent_object, source='archivesspace').identifier
            self.collection = self.source_object.data['resource']
            for transfer in self.data['transfers']:
                if not self.create_component(transfer):
                    self.log.error("Error creating component", object=transfer['url'])
                    return False
            self.source_object.process_status = 50
            self.source_object.save()

    def create_grouping_component(self):
        self.log.bind(request_id=str(uuid4()))
        consumer_data = self.transformer.transform_grouping_component(self.data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        if (consumer_data and aspace_identifier):
            ConsumerObject().initial_save(consumer_data=consumer_data, identifier=aspace_identifier, type='component', source_object=self.source_object)
            return True
        return False

    def create_component(self, data):
        self.log.bind(request_id=str(uuid4()))
        source_data = self.aurora_client.get(data['url'])
        self.transformer.parent = self.parent
        consumer_data = self.transformer.transform_component(source_data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        source_data['parents'].append({"identifier": self.parent, "source": "archivesspace"})
        source_data['collections'].append({"identifier": self.collection, "source": "archivesspace"})
        source_data['external_identifiers'].append({"identifier": aspace_identifier, "source": "archivesspace"})
        if self.aurora_client.update(data['url'], data=source_data):
            ConsumerObject().initial_save(consumer_data=consumer_data, identifier=aspace_identifier, type='component', source_data=source_data)
            return True
        return False