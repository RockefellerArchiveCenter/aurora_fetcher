from aquarius import settings

from .clients import ArchivesSpaceClient, ArchivesSpaceClientAccessionNumberError, UrsaMajorClient, AuroraClient
from .models import Package
from .transformers import DataTransformer


class RoutineError(Exception): pass
class UpdateRequestError(Exception): pass


class Routine:
    """
    Base class which is inherited by all other routines.

    Provides default clients for ArchivesSpace and Ursa Major, and instantiates
    a DataTransformer class.

    The `apply_transformations` method in the `run` function is intended to be
    overriden by routines which interact with specific types of objects.
    Requires the following variables to be overriden as well:
        start_status - the status of the objects to be acted on.
        end_status - the status to be applied to Package objects once the
                        routine has completed successfully.
        object_type = a string containing the object type of the routine.
    """

    def __init__(self):
        self.aspace_client = ArchivesSpaceClient(settings.ARCHIVESSPACE['baseurl'],
                                                 settings.ARCHIVESSPACE['username'],
                                                 settings.ARCHIVESSPACE['password'],
                                                 settings.ARCHIVESSPACE['repo_id'])
        self.ursa_major_client = UrsaMajorClient(settings.URSA_MAJOR['baseurl'])
        self.transformer = DataTransformer(aspace_client=self.aspace_client)

    def run(self):
        package_ids = []

        for package in Package.objects.filter(process_status=self.start_status):
            try:
                package.refresh_from_db()
                self.apply_transformations(package)
                package.process_status = self.end_status
                package.save()
                package_ids.append(package.identifier)
            except Exception as e:
                raise RoutineError("{} error: {}".format(self.object_type, e), package.identifier)
        message = ("{} created.".format(self.object_type) if (len(package_ids) > 0)
                   else "{} updated.".format(self.object_type))
        return (message, package_ids)


class AccessionRoutine(Routine):
    """Transforms accession data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an accession record."""

    start_status = Package.SAVED
    end_status = Package.ACCESSION_CREATED
    object_type = "Accession"

    def apply_transformations(self, package):
        package.transfer_data = self.ursa_major_client.find_bag_by_id(package.identifier)
        self.discover_sibling_data(package)
        if not package.accession_data:
            package.accession_data = self.ursa_major_client.retrieve(package.transfer_data['accession'])
        if not package.accession_data['data'].get('archivesspace_identifier'):
            self.transformer.package = package
            transformed_data = self.transformer.transform_accession()
            self.save_new_accession(transformed_data)

    def discover_sibling_data(self, package):
        if Package.objects.filter(transfer_data__accession=package.transfer_data['accession'], accession_data__isnull=False).exists():
            sibling = Package.objects.filter(transfer_data__accession=package.transfer_data['accession'], accession_data__isnull=False)[0]
            package.accession_data = sibling.accession_data
            package.transfer_data['data']['archivesspace_parent_identifier'] = sibling.transfer_data['data'].get('archivesspace_parent_identifier')

    def parse_accession_number(self, data):
        number = "{}".format(data['id_0'])
        if data.get('id_1'):
            number += ":{}".format(data['id_1'])
        if data.get('id_2'):
            number += ":{}".format(data['id_2'])
        return number

    def save_new_accession(self, data):
        try:
            accession_uri = self.aspace_client.create(data, 'accession').get('uri')
            self.transformer.package.accession_data['data']['archivesspace_identifier'] = accession_uri
            self.transformer.package.accession_data['data']['accession_number'] = self.parse_accession_number(data)
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

    start_status = Package.ACCESSION_UPDATE_SENT
    end_status = Package.GROUPING_COMPONENT_CREATED
    object_type = "Grouping component"

    def apply_transformations(self, package):
        if not package.transfer_data['data'].get('archivesspace_parent_identifier'):
            self.transformer.package = package
            self.parent = self.save_new_grouping_component()
            package.transfer_data['data']['archivesspace_parent_identifier'] = self.parent
            self.update_siblings(package)

    def save_new_grouping_component(self):
        transformed_data = self.transformer.transform_grouping_component()
        return self.aspace_client.create(transformed_data, 'component').get('uri')

    def update_siblings(self, package):
        for p in package.accession_data['data']['transfers']:
            for sibling in Package.objects.filter(identifier=p['identifier']):
                sibling.transfer_data['data']['archivesspace_parent_identifier'] = self.parent
                sibling.save()


class TransferComponentRoutine(Routine):
    """Transforms transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as an archival object record."""

    start_status=Package.GROUPING_COMPONENT_CREATED
    end_status = Package.TRANSFER_COMPONENT_CREATED
    object_type = "Transfer component"

    def apply_transformations(self, package):
        if not package.transfer_data['data'].get('archivesspace_identifier'):
            self.transformer.package = package
            self.transfer_identifier = self.save_new_transfer_component()
            package.transfer_data['data']['archivesspace_identifier'] = self.transfer_identifier
            self.update_siblings(package)

    def save_new_transfer_component(self):
        transformed_data = self.transformer.transform_component()
        return self.aspace_client.create(transformed_data, 'component').get('uri')

    def update_siblings(self, package):
        for sibling in Package.objects.filter(identifier=package.identifier):
            sibling.transfer_data['data']['archivesspace_identifier'] = self.transfer_identifier
            sibling.save()


class DigitalObjectRoutine(Routine):
    """Transforms transfer data stored in Ursa Major and delivers the
       transformed data to ArchivesSpace where it is saved as a digital object record."""

    start_status = Package.TRANSFER_COMPONENT_CREATED
    end_status = Package.DIGITAL_OBJECT_CREATED
    object_type = "Digital object"

    def apply_transformations(self, package):
        self.transformer.package = package
        self.do_identifier = self.save_new_digital_object()
        self.update_instance(package)

    def save_new_digital_object(self):
        transformed_data = self.transformer.transform_digital_object()
        return self.aspace_client.create(transformed_data, 'digital object').get('uri')

    def update_instance(self, package):
        transfer_component = self.aspace_client.retrieve(package.transfer_data['data']['archivesspace_identifier'])
        transfer_component['instances'].append(
            {"instance_type": "digital_object",
             "jsonmodel_type": "instance",
             "digital_object": {"ref": self.do_identifier}
             })
        updated_component = self.aspace_client.update(package.transfer_data['data']['archivesspace_identifier'], transfer_component)


class AuroraUpdater:
    """
    Base class for routines that interact with Aurora. Provides a web client
    and a `run` method.

    To use this class, override the `update_data` method. This method specifies
    the data object to be delivered to Aurora, as well as any changes to that
    object. Classes inheriting this class should also specify a `start_status`
    and an `end_status`, which determine the queryset of objects acted on and
    the status to which those objects are updated, respectively.
    """
    def __init__(self):
        self.client = AuroraClient(baseurl=settings.AURORA['baseurl'],
                                   username=settings.AURORA['username'],
                                   password=settings.AURORA['password'])

    def run(self):
        update_ids = []
        for obj in Package.objects.filter(process_status=self.start_status):
            try:
                data = self.update_data(obj)
                identifier = data['url'].rstrip('/').split('/')[-1]
                prefix = data['url'].rstrip('/').split('/')[-2]
                url = "/".join([prefix, "{}/".format(identifier.lstrip('/'))])
                r = self.client.update(url, data=data)
                obj.process_status = self.end_status
                obj.save()
                update_ids.append(obj.identifier)
            except Exception as e:
                raise UpdateRequestError(e)
        return ("Update requests sent.", update_ids)


class TransferUpdateRequester(AuroraUpdater):
    """Updates transfer data in Aurora."""
    start_status = Package.DIGITAL_OBJECT_CREATED
    end_status = Package.UPDATE_SENT

    def update_data(self, obj):
        data = obj.transfer_data['data']
        data['process_status'] = 90
        return data


class AccessionUpdateRequester(AuroraUpdater):
    """Updates accession data in Aurora."""
    start_status = Package.ACCESSION_CREATED
    end_status = Package.ACCESSION_UPDATE_SENT

    def update_data(self, obj):
        data = obj.accession_data['data']
        data['process_status'] = 30
        return data
