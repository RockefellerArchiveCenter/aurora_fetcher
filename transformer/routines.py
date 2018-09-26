import json
import logging
import requests
from os import path
from structlog import wrap_logger
from uuid import uuid4

from aquarius import settings

from .clients import ArchivesSpaceClient
from .models import Transfer
from .transformers import DataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferRoutine:
    def __init__(self, aspace_client):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.transformer = DataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self, transfer):
        self.log.bind(request_id=str(uuid4()))

        if int(transfer.process_status) <= 20:
            transfer.transfer_data = self.get_transfer_data(transfer)
            if 'accession' not in transfer.transfer_data['external_identifiers']:
                accession_data = self.get_accession_data(transfer)
                transfer.accession_data = accession_data
                transformed_data = self.transformer.transform_accession(transfer.accession_data)
                accession_identifier = self.aspace_client.create(transformed_data, 'accession')
                if not accession_identifier:
                    return False
                accession_external_identifier = {"identifier": accession_identifier,
                                                 "source": "archivesspace",
                                                 "type": "accession"}
                for t in transfer.accession_data['transfers']:
                    t.transfer_data['external_identifiers'].append(accession_external_identifier)
                    self.update_identifier(t.transfer_data)
            transfer.process_status = 20
            transfer.save()

        if int(transfer.process_status) <= 30:
            if 'grouping_component' not in transfer.transfer_data['external_identifiers']:
                transformed_data = self.transformer.transform_grouping_component(transfer.accession_data)
                grouping_identifier = self.aspace_client.create(transformed_data, 'component')
                self.transformer.parent = grouping_identifier
                self.transformer.resource = transfer.accession_data['resource']
                if not grouping_identifier:
                    return False
                grouping_external_identifier = {"identifier": grouping_identifier,
                                                "source": "archivesspace",
                                                "type": "grouping_component"}
                for t in transfer.accession_data['transfers']:
                    t.transfer_data['external_identifiers'].append(grouping_external_identifier)
                    self.update_identifier(t.transfer_data)
            transfer.process_status = 30
            transfer.save()

        if int(transfer.process_status) <= 40:
            transformed_data = self.transformer.transform_component(transfer.transfer_data)
            transfer_identifier = self.aspace_client.create(transformed_data, 'component')
            if not transfer_identifier:
                return False
            transfer_external_identifier = {"identifier": transfer_identifier,
                                            "source": "archivesspace",
                                            "type": "transfer_component"}
            transfer.transfer_data['external_identifiers'].append(transfer_external_identifier)
            self.update_identifier(transfer.transfer_data)
            transfer.process_status = 40
            transfer.save()

    def get_transfer_data(self, transfer):
        # transfer = find_by_id(transfer.identifier)
        # return transfer
        json_file = open(path.join(settings.BASE_DIR, 'fixtures/data/fetch/transfer.json'), 'r')
        return json.load(json_file)

    def get_accession_data(self, transfer):
        # transfer = find_by_id(transfer.identifier)
        # return transfer
        json_file = open(path.join(settings.BASE_DIR, 'fixtures/data/fetch/accession.json'), 'r')
        return json.load(json_file)

    def update_identifier(self, data):
        # transfer = find_by_id(data['identifier'])
        # transfer.data = data (or whatever the field name is)
        # POST transfer back to data['url']
        pass
