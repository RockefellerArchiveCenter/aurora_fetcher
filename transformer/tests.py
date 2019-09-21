import json
import time
from os import listdir
from os.path import join
import vcr

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from aquarius import settings
from .models import Package
from .routines import *
from .views import *

transformer_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir=join(settings.BASE_DIR, 'fixtures/cassettes'),
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)


class TransformTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.transfer_data = []
        self.transfer_count = 0
        for file in sorted(listdir(join(settings.BASE_DIR, 'fixtures/data'))):
            with open(join(settings.BASE_DIR, 'fixtures/data/{}'.format(file)), 'r') as json_file:
                data = json.load(json_file)
                self.transfer_data.append(data)
                self.transfer_count += 1
        self.updated_time = int(time.time())-(24*3600) # this is the current time minus 24 hours

    def create_transfers(self):
        print('*** Creating Packages ***')
        for transfer in self.transfer_data:
            request = self.factory.post(reverse('package-list'), transfer, format='json')
            response = PackageViewSet.as_view(actions={"post": "create"})(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(len(self.transfer_data), len(Package.objects.all()))

    def process_transfers(self):
        ROUTINES = (
            ('process_accessions.json', AccessionRoutine, Package.ACCESSION_CREATED),
            ('process_grouping.json', GroupingComponentRoutine, Package.GROUPING_COMPONENT_CREATED),
            ('process_transfers.json', TransferComponentRoutine, Package.TRANSFER_COMPONENT_CREATED),
        )
        for r in ROUTINES:
            with transformer_vcr.use_cassette(r[0]):
                accessions = r[1]().run()
                self.assertNotEqual(False, accessions)
                for transfer in Package.objects.all():
                    self.assertEqual(int(transfer.process_status), r[2])

        DIGITAL_ROUTINES = (
            ('process_digital.json', DigitalObjectRoutine, Package.DIGITAL_OBJECT_CREATED),
            ('send_update.json', TransferUpdateRequester, Package.UPDATE_SENT)
        )
        for d in DIGITAL_ROUTINES:
            with transformer_vcr.use_cassette(d[0]):
                digital = d[1]().run()
                self.assertNotEqual(False, digital)
                for transfer in Package.objects.all().order_by('-last_modified')[:2]:
                    self.assertEqual(int(transfer.process_status), d[2])

        self.assertEqual(len(Package.objects.all()), self.transfer_count)

    def search_objects(self):
        print('*** Searching for objects ***')
        request = self.factory.get(reverse('package-list'), {'updated_since': self.updated_time})
        response = PackageViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertTrue(len(response.data) >= 1, "No search results")

    def process_views(self):
        print('*** Test ProcessAccessionsView ***')
        VIEWS = (
            ('process_accessions.json', 'accessions', ProcessAccessionsView),
            ('process_grouping.json', 'grouping-components', ProcessGroupingComponentsView),
            ('process_transfers.json', 'transfer-components', ProcessTransferComponentsView),
            ('process_digital.json', 'digital-objects', ProcessDigitalObjectsView),
            ('send_update.json', 'send-update', TransferUpdateRequestView),
            ('send_accession_update.json', 'send-accession-update', AccessionUpdateRequestView),
        )
        for v in VIEWS:
            with transformer_vcr.use_cassette(v[0]):
                request = self.factory.post(reverse(v[1]))
                response = v[2].as_view()(request)
                self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def schema(self):
        print('*** Getting schema view ***')
        schema = self.client.get(reverse('schema'))
        self.assertEqual(schema.status_code, 200, "Wrong HTTP code")

    def health_check(self):
        print('*** Getting status view ***')
        status = self.client.get(reverse('api_health_ping'))
        self.assertEqual(status.status_code, 200, "Wrong HTTP code")

    def test_components(self):
        self.create_transfers()
        self.process_transfers()
        self.search_objects()
        self.process_views()
        self.schema()
        self.health_check()
