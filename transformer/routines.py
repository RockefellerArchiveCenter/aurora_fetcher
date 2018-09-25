import logging
from structlog import wrap_logger
from uuid import uuid4

from .clients import ArchivesSpaceClient
from .models import Transfer, Identifier
from .transformers import ArchivesSpaceDataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferRoutine:
    def __init__(self, aspace_client):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.transformer = ArchivesSpaceDataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self, transfer):
        self.log.bind(request_id=str(uuid4()))

        print(transfer.process_status)

        if int(transfer.process_status) <= 20:
            # Get transfer data
            # Save transfer data
            # if not accession exists:
                # get accession data
                # save accession data
                # transform accession data
                # post accession data to AS
                # save identifier
                # post identifier to Ursa Major
            transfer.process_status = 20
            transfer.save()

        if int(transfer.process_status) <= 30:
            # if not grouping component exists: BUT HOW WILL I KNOW??
                # transform accession data
                # post grouping component to AS
                # save identifier
                # post identifier to UM
            transfer.process_status = 30
            transfer.save()

        if int(transfer.process_status) <= 40:
            # transform transfer_data
            # post transfer to AS
            # save identifier
            # post identifier to UM
            transfer.process_status = 40
            transfer.save()

    def create_grouping_component(self):
        self.log.bind(request_id=str(uuid4()))
        consumer_data = self.transformer.transform_grouping_component(self.data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        if (consumer_data and aspace_identifier):
            ConsumerObject().initial_save(
                consumer_data=consumer_data, identifier=aspace_identifier,
                type='component', source_object=self.source_object)
            return True
        return False

    def update_identifier(self, identifiers, new_identifier):
        for identifier in identifiers:
            if identifier['source'] == 'archivesspace':
                identifier['identifier'] = new_identifier
                return True
        return False

    def create_component(self, data):
        self.log.bind(request_id=str(uuid4()))
        source_data = self.aurora_client.retrieve(data['url'])
        self.transformer.parent = self.parent
        self.transformer.collection = self.collection
        consumer_data = self.transformer.transform_component(source_data)
        aspace_identifier = self.aspace_client.create(consumer_data, 'component')
        IDENTIFIERS = (
            (source_data['parents'], self.parent),
            (source_data['collections'], self.collection),
            (source_data['external_identifiers'], aspace_identifier)
        )
        # If an ArchivesSpace identifier exists, update it. If not, add a new identifier.
        for t in IDENTIFIERS:
            if not self.update_identifier(t[0], t[1]):
                t[0].append({"identifier": t[1], "source": "archivesspace"})
        if self.aurora_client.update(data['url'], data=source_data):
            ConsumerObject().initial_save(
                consumer_data=consumer_data, identifier=aspace_identifier,
                type='component', source_data=source_data)
            return True
        return False
