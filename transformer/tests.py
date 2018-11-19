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
from .routines import AccessionRoutine, GroupingComponentRoutine, TransferComponentRoutine, DigitalObjectRoutine, UpdateRequester
from .views import PackageViewSet, ProcessAccessionsView, UpdateRequestView

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
        for file in listdir(join(settings.BASE_DIR, 'fixtures/data')):
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
            print('Created transfer {url}'.format(url=response.data['url']))
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(len(self.transfer_data), len(Package.objects.all()))

    def process_transfers(self):
        with transformer_vcr.use_cassette('process_accessions.json'):
            print('*** Processing Accessions ***')
            accessions = AccessionRoutine().run()
            self.assertNotEqual(False, accessions)
            for transfer in Package.objects.all():
                self.assertEqual(int(transfer.process_status), Package.ACCESSION_CREATED)

        with transformer_vcr.use_cassette('process_grouping.json'):
            print('*** Processing Grouping Components ***')
            grouping = GroupingComponentRoutine().run()
            self.assertNotEqual(False, grouping)
            for transfer in Package.objects.all():
                self.assertEqual(int(transfer.process_status), Package.GROUPING_COMPONENT_CREATED)

        with transformer_vcr.use_cassette('process_transfers.json'):
            print('*** Processing Transfer Components ***')
            transfers = TransferComponentRoutine().run()
            self.assertNotEqual(False, transfers)
            for transfer in Package.objects.all():
                self.assertEqual(int(transfer.process_status), Package.TRANSFER_COMPONENT_CREATED)

        with transformer_vcr.use_cassette('process_digital.json'):
            print('*** Processing Digital Objects ***')
            digital = DigitalObjectRoutine().run()
            self.assertNotEqual(False, digital)
            for transfer in Package.objects.all():
                self.assertEqual(int(transfer.process_status), Package.DIGITAL_OBJECT_CREATED)

        # with transformer_vcr.use_cassette('send_update.json'):
        #     print('*** Sending update request ***')
        #     update = UpdateRequester('http://web:8000/api/transfers/').run()
        #     self.assertNotEqual(False, update)
        #     for transfer in Package.objects.all():
        #         self.assertEqual(int(transfer.process_status), Package.UPDATE_SENT)

            self.assertEqual(len(Package.objects.all()), self.transfer_count)

    def search_objects(self):
        print('*** Searching for objects ***')
        request = self.factory.get(reverse('package-list'), {'updated_since': self.updated_time})
        response = PackageViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertTrue(len(response.data) >= 1, "No search results")

    def process_views(self):
        print('*** Test ProcessAccessionsView ***')
        with transformer_vcr.use_cassette('process_accessions.json'):
            request = self.factory.post(reverse('accessions'))
            response = ProcessAccessionsView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

        with transformer_vcr.use_cassette('process_grouping.json'):
            request = self.factory.post(reverse('grouping-components'))
            response = ProcessAccessionsView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

        with transformer_vcr.use_cassette('process_transfers.json'):
            request = self.factory.post(reverse('transfer-components'))
            response = ProcessAccessionsView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

        with transformer_vcr.use_cassette('process_digital.json'):
            request = self.factory.post(reverse('digital-objects'))
            response = ProcessAccessionsView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

        # with transformer_vcr.use_cassette('send_update.json'):
        #     request = self.factory.post(reverse('send-update'))
        #     response = UpdateRequestView.as_view()(request)
        #     self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def schema(self):
        print('*** Getting schema view ***')
        schema = self.client.get(reverse('schema-json', kwargs={"format": ".json"}))
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
