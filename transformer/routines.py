import logging
from structlog import wrap_logger
from uuid import uuid4

from client.clients import ArchivesSpaceClient, AuroraClient
from transformer.models import SourceObject, ConsumerObject, Identifier
from transformer.transformers import ArchivesSpaceDataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class AccessionRoutine:
    def __init__(self, source_object):
        self.source_object = source_object
        self.data = source_object.data
        self.log = logger

    def run(self):
        self.log.bind(request_id=str(uuid4()))
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
        transformer = ArchivesSpaceDataTransformer()
        aspace_client = ArchivesSpaceClient()
        consumer_data = transformer.transform_grouping_component(self.data)
        aspace_identifier = aspace_client.save_data(consumer_data, 'component')
        if (consumer_data and aspace_identifier):
            consumer_object = ConsumerObject.objects.create(
                consumer='archivesspace',
                type='component',
                source_object=self.source_object,
                data=consumer_data,
            )
            self.log.debug("Created ConsumerObject", object=consumer_object)
            print(consumer_object)
            identifier = Identifier.objects.create(
                source='archivesspace',
                identifier=aspace_identifier,
                consumer_object=consumer_object,
            )
            self.log.debug("Created Identifier", object=identifier)
            return True
        return False

    def create_component(self, data):
        self.log.bind(request_id=str(uuid4()))
        transformer = ArchivesSpaceDataTransformer()
        aspace_client = ArchivesSpaceClient()
        aurora_client = AuroraClient()
        source_data = aurora_client.get_data(data['url'])
        source_data['parent'] = self.parent
        source_data['collection'] = self.collection
        consumer_data = transformer.transform_component(source_data)
        aspace_identifier = aspace_client.save_data(consumer_data, 'component')
        # TODO: create external identifier object for component and add to data
        if aurora_client.update_data(data['url'], data=source_data):
            source_object = SourceObject.objects.create(
                source='aurora',
                type='component',
                data=source_data,
                process_status=10,
            )
            self.log.debug("Created SourceObject", object=source_object)
            consumer_object = ConsumerObject.objects.create(
                consumer='archivesspace',
                type='component',
                source_object=source_object,
                data=consumer_data,
            )
            self.log.debug("Created ConsumerObject", object=consumer_object)
            identifier = Identifier.objects.create(
                source='archivesspace',
                identifier=aspace_identifier,
                consumer_object=consumer_object,
            )
            self.log.debug("Created Identifier", object=identifier)
            return True
        return False
