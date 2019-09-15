from aquarius import settings

from .clients import ArchivesSpaceClient, ArchivesSpaceClientAccessionNumberError, UrsaMajorClient, AuroraClient
from .models import Package
from .transformers import DataTransformer


class RoutineError(Exception): pass
class UpdateRequestError(Exception): pass


class Routine:
    """Base class which is inherited by all other routines."""

    def __init__(self):
        self.aspace_client = ArchivesSpaceClient(settings.ARCHIVESSPACE['baseurl'],
                                                 settings.ARCHIVESSPACE['username'],
                                                 settings.ARCHIVESSPACE['password'],
                                                 settings.ARCHIVESSPACE['repo_id'])
        self.ursa_major_client = UrsaMajorClient(settings.URSA_MAJOR['baseurl'])
        self.transformer = DataTransformer(aspace_client=self.aspace_client)


class AccessionRoutine(Routine):
    """Transforms accession data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an accession record."""

    def run(self):
        packages = Package.objects.filter(process_status=Package.SAVED)
        package_ids = []
        accession_created = False

        for package in packages:
            try:
                package.refresh_from_db()
                package.transfer_data = self.ursa_major_client.find_bag_by_id(package.identifier)
                self.discover_sibling_data(package)
                if not package.accession_data:
                    package.accession_data = self.ursa_major_client.retrieve(package.transfer_data['accession'])
                if not package.accession_data['data'].get('archivesspace_identifier'):
                    self.transformer.package = package
                    transformed_data = self.transformer.transform_accession()
                    self.save_new_accession(transformed_data)
                    accession_created = True
                package.process_status = Package.ACCESSION_CREATED
                package.save()
                package_ids.append(package.identifier)
            except Exception as e:
                raise RoutineError("Accession error: {}".format(e), package.identifier)
        message = "Accession created." if accession_created else "Accession updated."
        return (message, package_ids)

    def discover_sibling_data(self, package):
        if Package.objects.filter(transfer_data__accession=package.transfer_data['accession'], accession_data__isnull=False).exists():
            sibling = Package.objects.filter(transfer_data__accession=package.transfer_data['accession'], accession_data__isnull=False)[0]
            package.accession_data = sibling.accession_data
            package.transfer_data['data']['archivesspace_parent_identifier'] = sibling.transfer_data['data'].get('archivesspace_parent_identifier')

    def save_new_accession(self, data):
        try:
            accession_identifier = self.aspace_client.create(data, 'accession')
            self.transformer.package.accession_data['data']['archivesspace_identifier'] = accession_identifier
            for p in self.transformer.package.accession_data['data']['transfers']:
                for sibling in Package.objects.filter(identifier=p['identifier']):
                    sibling.accession_data = self.transformer.package.accession_data
                    sibling.save()
        except ArchivesSpaceClientAccessionNumberError:
            """Account for indexing delays by bumping up to the next accession number."""
            id_1 = int(data['id_1'])
            id_1 += 1
            data['id_1'] = str(id_1).zfill(3)
            self.save_new_accession(data)
        except Exception as e:
            raise RoutineError("Error saving data in ArchivesSpace: {}".format(e), self.transformer.package.identifier)


class GroupingComponentRoutine(Routine):
    """Transforms accession data stored in Ursa Major into a grouping component
       and delivers the transformed data to ArchivesSpace where it is saved
       as an archival object record."""

    def run(self):
        packages = Package.objects.filter(process_status=Package.ACCESSION_CREATED)
        package_ids = []
        grouping_created = False

        for package in packages:
            try:
                package.refresh_from_db()
                if not package.transfer_data['data'].get('archivesspace_parent_identifier'):
                    self.transformer.package = package
                    self.parent = self.save_new_grouping_component()
                    package.transfer_data['data']['archivesspace_parent_identifier'] = self.parent
                    self.update_siblings(package)
                    grouping_created = True
                package.process_status = package.GROUPING_COMPONENT_CREATED
                package.save()
                package_ids.append(package.identifier)
            except Exception as e:
                raise RoutineError("Grouping component error: {}".format(e), package.identifier)
        message = "Grouping component created." if grouping_created else "Grouping component updated."
        return (message, package_ids)

    def save_new_grouping_component(self):
        transformed_data = self.transformer.transform_grouping_component()
        return self.aspace_client.create(transformed_data, 'component')

    def update_siblings(self, package):
        for p in package.accession_data['data']['transfers']:
            for sibling in Package.objects.filter(identifier=p['identifier']):
                sibling.transfer_data['data']['archivesspace_parent_identifier'] = self.parent
                sibling.save()


class TransferComponentRoutine(Routine):
    """Transforms transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an archival object record."""

    def run(self):
        packages = Package.objects.filter(process_status=Package.GROUPING_COMPONENT_CREATED)
        package_ids = []
        transfer_created = False

        for package in packages:
            try:
                package.refresh_from_db()
                if not package.transfer_data['data'].get('archivesspace_identifier'):
                    self.transformer.package = package
                    self.transfer_identifier = self.save_new_transfer_component()
                    package.transfer_data['data']['archivesspace_identifier'] = self.transfer_identifier
                    self.update_siblings(package)
                    transfer_created = True
                package.process_status = Package.TRANSFER_COMPONENT_CREATED
                package.save()
                package_ids.append(package.identifier)
            except Exception as e:
                raise RoutineError("Transfer component error: {}".format(e), package.identifier)
        message = "Transfer component created." if transfer_created else "Transfer component updated."
        return (message, package_ids)

    def save_new_transfer_component(self):
        transformed_data = self.transformer.transform_component()
        return self.aspace_client.create(transformed_data, 'component')

    def update_siblings(self, package):
        for sibling in Package.objects.filter(identifier=package.identifier):
            sibling.transfer_data['data']['archivesspace_identifier'] = self.transfer_identifier
            sibling.save()


class DigitalObjectRoutine(Routine):
    """Transforms transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as a digital object record."""

    def run(self):
        packages = Package.objects.filter(process_status=Package.TRANSFER_COMPONENT_CREATED).order_by('last_modified')[:2]
        digital_ids = []

        for package in packages:
            try:
                package.refresh_from_db()
                self.transformer.package = package
                self.do_identifier = self.save_new_digital_object()
                self.update_instance(package)
                package.process_status = Package.DIGITAL_OBJECT_CREATED
                package.save()
                digital_ids.append(package.identifier)
            except Exception as e:
                raise RoutineError("Digital object error: {}".format(e), package.identifier)
        return ("Digital objects created.", digital_ids)

    def save_new_digital_object(self):
        transformed_data = self.transformer.transform_digital_object()
        return self.aspace_client.create(transformed_data, 'digital object')

    def update_instance(self, package):
        transfer_component = self.aspace_client.retrieve(package.transfer_data['data']['archivesspace_identifier'])
        transfer_component['instances'].append(
            {"instance_type": "digital_object",
             "jsonmodel_type": "instance",
             "digital_object": {"ref": self.do_identifier}
             })
        updated_component = self.aspace_client.update(package.transfer_data['data']['archivesspace_identifier'], transfer_component)


class UpdateRequester:
    def __init__(self):
        self.client = AuroraClient(baseurl=settings.AURORA['baseurl'],
                                   username=settings.AURORA['username'],
                                   password=settings.AURORA['password'])

    def run(self):
        update_ids = []
        for package in Package.objects.filter(process_status=Package.DIGITAL_OBJECT_CREATED):
            try:
                data = package.transfer_data['data']
                data['process_status'] = 90
                identifier = data['url'].rstrip('/').split('/')[-1]
                url = "/".join(["transfers", "{}/".format(identifier.lstrip('/'))])
                r = self.client.update(url, data=data)
                package.process_status = Package.UPDATE_SENT
                package.save()
                update_ids.append(package.identifier)
            except Exception as e:
                raise UpdateRequestError(e)
        return ("Update requests sent.", update_ids)
