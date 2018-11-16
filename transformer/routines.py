import json
import logging
from structlog import wrap_logger
from uuid import uuid4

from aquarius import settings

from .clients import ArchivesSpaceClient, UrsaMajorClient
from .models import Package
from .transformers import DataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger = wrap_logger(logger)


class RoutineError(Exception): pass


class Routine:
    """Base class which is inherited by all other routines."""

    def __init__(self):
        self.aspace_client = ArchivesSpaceClient(settings.ARCHIVESSPACE['baseurl'],
                                                 settings.ARCHIVESSPACE['username'],
                                                 settings.ARCHIVESSPACE['password'],
                                                 settings.ARCHIVESSPACE['repo_id'])
        self.ursa_major_client = UrsaMajorClient(settings.URSA_MAJOR['baseurl'])
        self.transformer = DataTransformer(aspace_client=self.aspace_client)
        self.log = logger

    def bind_log(self):
        self.log.bind(request_id=str(uuid4()))


class AccessionRoutine(Routine):
    """Transforms Accession data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an accession record."""

    def run(self):
        self.bind_log()
        packages = Package.objects.filter(process_status=10)
        accession_count = 0

        for package in packages:
            self.log.debug("Running AccessionTransferRoutine", object=package)
            try:
                package.transfer_data = self.ursa_major_client.find_bag_by_id(package.identifier)
                package.accession_data = self.ursa_major_client.retrieve(package.transfer_data['accession'])
                if not package.accession_data.get('archivesspace_identifier'):
                    self.transformer.object = package
                    self.save_new_accession(package)
                    accession_count += 1
                package.process_status = 20
                package.save()
            except Exception as e:
                raise RoutineError("Accession error: {}".format(e))
        return "{} accessions saved.".format(accession_count)

    def save_new_accession(self, package):
        transformed_data = self.transformer.transform_accession(package.accession_data['data'])
        accession_identifier = self.aspace_client.create(transformed_data, 'accession')
        package.accession_data['archivesspace_identifier'] = accession_identifier
        for p in package.accession_data['data']['transfers']:
            for sibling in Package.objects.filter(identifier=p['identifier']):
                sibling.accession_data = package.accession_data
                sibling.save()


class GroupingComponentRoutine(Routine):
    """Transforms Accession data stored in Ursa Major into a grouping component
       and delivers the transformed data to ArchivesSpace where it is saved
       as an archival object record."""

    def run(self):
        self.bind_log()
        packages = Package.objects.filter(process_status=20)
        grouping_count = 0

        for p in packages:
            try:
                package = Package.objects.get(id=p.pk)
                if not package.transfer_data.get('archivesspace_parent_identifier'):
                    self.transformer.object = package
                    self.save_new_grouping_component(package)
                    grouping_count += 1
                package.process_status = 30
                package.save()
            except Exception as e:
                raise RoutineError("Grouping component error: {}".format(e))
        return "{} grouping components saved.".format(grouping_count)

    def save_new_grouping_component(self, package):
        transformed_data = self.transformer.transform_grouping_component(package.accession_data['data'])
        parent = self.aspace_client.create(transformed_data, 'component')
        package.transfer_data['archivesspace_parent_identifier'] = parent
        for p in package.accession_data['data']['transfers']:
            for sibling in Package.objects.filter(identifier=p['identifier']):
                sibling.transfer_data['archivesspace_parent_identifier'] = parent
                sibling.save()


class TransferComponentRoutine(Routine):
    """Transforms Transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an archival object record."""

    def run(self):
        self.bind_log()
        packages = Package.objects.filter(process_status=30)
        transfer_count = 0

        for p in packages:
            try:
                package = Package.objects.get(id=p.pk)
                if not package.transfer_data.get('archivesspace_identifier'):
                    self.transformer.object = package
                    # TODO: might not need the below
                    self.transformer.resource = package.accession_data['data']['resource']
                    self.transformer.parent = package.transfer_data['archivesspace_parent_identifier']
                    self.save_new_transfer_component(package)
                    transfer_count += 1
                package.process_status = 40
                package.save()
            except Exception as e:
                raise RoutineError("Transfer component error: {}".format(e))
        return "{} transfer components created.".format(transfer_count)

    def save_new_transfer_component(self, package):
        transformed_data = self.transformer.transform_component(package.transfer_data['data'])
        transfer_identifier = self.aspace_client.create(transformed_data, 'component')
        package.transfer_data['archivesspace_identifier'] = transfer_identifier
        for sibling in Package.objects.filter(identifier=package.identifier):
            sibling.transfer_data['archivesspace_identifier'] = transfer_identifier
            sibling.save()


class DigitalObjectRoutine(Routine):
    """Transforms Transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as a digital object record."""

    def run(self):
        self.bind_log()
        packages = Package.objects.filter(process_status=40)
        digital_count = 0

        for p in packages:
            try:
                package = Package.objects.get(id=p.pk)
                self.transformer.object = package
                self.save_new_digital_object(package)
                digital_count += 1
                package.process_status = 50
                package.save()
            except Exception as e:
                raise RoutineError("Digital object error: {}".format(e))
        return "{} digital objects saved.".format(digital_count)

    def save_new_digital_object(self, package):
        transformed_data = self.transformer.transform_digital_object(package)
        do_identifier = self.aspace_client.create(transformed_data, 'digital object')
        transfer_component = self.aspace_client.retrieve(package.transfer_data['archivesspace_identifier'])
        transfer_component['instances'].append(
            {"instance_type": "digital_object",
             "jsonmodel_type": "instance",
             "digital_object": {"ref": do_identifier}
             })
        updated_component = self.aspace_client.update(package.transfer_data['archivesspace_identifier'], transfer_component)
