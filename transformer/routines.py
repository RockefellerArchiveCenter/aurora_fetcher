import json
import logging
from structlog import wrap_logger
from uuid import uuid4

from aquarius import settings

from .clients import ArchivesSpaceClient, UrsaMajorClient
from .models import Transfer
from .transformers import DataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferRoutineError(Exception): pass


class TransferRoutine:
    def __init__(self):
        self.aspace_client = ArchivesSpaceClient()
        self.ursa_major_client = UrsaMajorClient()
        self.transformer = DataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def run(self):
        self.log.bind(request_id=str(uuid4()))
        transfers = Transfer.objects.filter(process_status__lte=20)
        self.log.debug("Found {} transfers to process".format(len(transfers)))
        transfer_count = 0

        for transfer in transfers:
            self.log.debug("Running transfer routine", object=transfer)
            if int(transfer.process_status) < 20:
                try:
                    transfer.transfer_data = self.ursa_major_client.find_bag_by_id(transfer.identifier)
                    transfer.accession_data = self.ursa_major_client.retrieve(transfer.transfer_data['accession'])
                    if not transfer.accession_data.get('archivesspace_identifier'):
                        self.save_new_accession(transfer)
                    transfer.process_status = 20
                    transfer.save()
                except Exception as e:
                    raise TransferRoutineError("Accession error: {}".format(e))

            if int(transfer.process_status) < 30:
                try:
                    if not transfer.transfer_data.get('archivesspace_parent_identifier'):
                        self.save_new_grouping_component(transfer)
                    else:
                        self.transformer.parent = transfer.transfer_data['archivesspace_parent_identifier']
                    self.transformer.resource = transfer.accession_data['data']['resource']
                    transfer.process_status = 30
                    transfer.save()
                except Exception as e:
                    raise TransferRoutineError("Grouping component error: {}".format(e))

            if int(transfer.process_status) < 40:
                try:
                    if not transfer.transfer_data.get('archivesspace_identifier'):
                        self.save_new_transfer_component(transfer)
                    transfer.process_status = 40
                    transfer.save()
                except Exception as e:
                    raise TransferRoutineError("Transfer component error: {}".format(e))

            if int(transfer.process_status) < 50:
                try:
                    self.save_new_digital_object(transfer)
                    transfer.process_status = 50
                    transfer.save()
                    transfer_count += 1
                except Exception as e:
                    raise TransferRoutineError("Digital object error: {}".format(e))

        return "{} transfers processed and delivered.".format(transfer_count)

    def save_new_accession(self, transfer):
        transformed_data = self.transformer.transform_accession(transfer.accession_data['data'])
        accession_identifier = self.aspace_client.create(transformed_data, 'accession')
        transfer.accession_data['archivesspace_identifier'] = accession_identifier
        self.ursa_major_client.update(transfer.accession_data['url'], data=transfer.accession_data)

    def save_new_grouping_component(self, transfer):
        transformed_data = self.transformer.transform_grouping_component(transfer.accession_data['data'])
        self.transformer.parent = self.aspace_client.create(transformed_data, 'component')
        transfer.transfer_data['archivesspace_parent_identifier'] = self.transformer.parent
        for t in transfer.accession_data['data']['transfers']:
            data = self.ursa_major_client.find_bag_by_id(t['identifier'])
            data['archivesspace_parent_identifier'] = self.transformer.parent
            self.ursa_major_client.update(data['url'], data=data)

    def save_new_transfer_component(self, transfer):
        transformed_data = self.transformer.transform_component(transfer.transfer_data['data'])
        transfer_identifier = self.aspace_client.create(transformed_data, 'component')
        transfer.transfer_data['archivesspace_identifier'] = transfer_identifier
        self.ursa_major_client.update(transfer.transfer_data['url'], data=transfer.transfer_data)

    def save_new_digital_object(self, transfer):
        transformed_data = self.transformer.transform_digital_object(transfer)
        do_identifier = self.aspace_client.create(transformed_data, 'digital object')
        transfer_component = self.aspace_client.retrieve(transfer.transfer_data['archivesspace_identifier'])
        transfer_component['instances'].append(
            {"instance_type": "digital_object",
             "jsonmodel_type": "instance",
             "digital_object": {"ref": do_identifier}
             })
        updated_component = self.aspace_client.update(transfer.transfer_data['archivesspace_identifier'], transfer_component)
