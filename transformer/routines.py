import json
import logging
from os import path
from structlog import wrap_logger
from uuid import uuid4
from urllib.parse import urlparse

from aquarius import settings

from .clients import ArchivesSpaceClient, UrsaMajorClient
from .models import Transfer
from .transformers import DataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferRoutineError(Exception): pass


class TransferRoutine:
    def __init__(self, aspace_client=None, ursa_major_client=None):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.ursa_major_client = ursa_major_client if ursa_major_client else UrsaMajorClient()
        self.transformer = DataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self, transfer):
        self.log.bind(request_id=str(uuid4()))

        if int(transfer.process_status) <= 20:
            try:
                transfer_data = self.ursa_major_client.find_bag_by_id(transfer.identifier)
                transfer.transfer_data = transfer_data
                accession_data = self.ursa_major_client.retrieve(transfer.transfer_data['accession'])
                transfer.accession_data = accession_data
                if not transfer.accession_data.get('archivesspace_identifier'):
                    transformed_data = self.transformer.transform_accession(transfer.accession_data['data'])
                    accession_identifier = self.aspace_client.create(transformed_data, 'accession')
                    transfer.accession_data['archivesspace_identifier'] = accession_identifier
                    updated = self.ursa_major_client.update(transfer.accession_data['url'], data=transfer.accession_data)
                transfer.process_status = 20
                transfer.save()
            except Exception as e:
                raise TransferRoutineError("Error with accession: {}".format(e))

        if int(transfer.process_status) <= 30:
            try:
                if not transfer.transfer_data.get('archivesspace_parent_identifier'):
                    transformed_data = self.transformer.transform_grouping_component(transfer.accession_data['data'])
                    self.transformer.parent = self.aspace_client.create(transformed_data, 'component')
                    for t in transfer.accession_data['data']['transfers']:
                        data = self.ursa_major_client.find_bag_by_id(t['identifier'])
                        data['archivesspace_parent_identifier'] = self.transformer.parent
                        self.ursa_major_client.update(data['url'], data=data)
                else:
                    self.transformer.parent = transfer.transfer_data['archivesspace_parent_identifier']
                self.transformer.resource = transfer.accession_data['data']['resource']
                transfer.process_status = 30
                transfer.save()
            except Exception as e:
                raise TransferRoutineError("Error with grouping component: {}".format(e))

        if int(transfer.process_status) <= 40:
            try:
                transformed_data = self.transformer.transform_component(transfer.transfer_data['data'])
                transfer_identifier = self.aspace_client.create(transformed_data, 'component')
                transfer.transfer_data['archivesspace_identifier'] = transfer_identifier
                self.ursa_major_client.update(transfer.transfer_data['url'], data=transfer.transfer_data)
                transfer.process_status = 40
                transfer.save()
            except Exception as e:
                raise TransferRoutineError("Error with transfer component: {}".format(e))
