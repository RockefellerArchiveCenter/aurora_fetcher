import json
import time
from os import listdir
from os.path import join
import vcr

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory

from aquarius import settings
from .cron import ProcessTransfers
from .models import Transfer
from .views import TransferViewSet, ProcessTransfersView

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
        for file in listdir(join(settings.BASE_DIR, 'fixtures/data/post')):
            with open(join(settings.BASE_DIR, 'fixtures/data/post/{}'.format(file)), 'r') as json_file:
                data = json.load(json_file)
                self.transfer_data.append(data)
                self.transfer_count += 1
        self.updated_time = int(time.time())-(24*3600) # this is the current time minus 24 hours

    def create_transfers(self):
        print('*** Creating Transfers ***')
        for transfer in self.transfer_data:
            request = self.factory.post(reverse('transfer-list'), transfer, format='json')
            response = TransferViewSet.as_view(actions={"post": "create"})(request)
            print('Created transfer {url}'.format(url=response.data['url']))
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(len(self.transfer_data), len(Transfer.objects.all()))

    def process_transfers(self):
        print('*** Processing Transfers ***')
        with transformer_vcr.use_cassette('process_transfers.json'):
            cron = ProcessTransfers().do()
            for transfer in Transfer.objects.all():
                self.assertEqual(int(transfer.process_status), 50)
            self.assertEqual(len(Transfer.objects.all()), self.transfer_count)

    def search_objects(self):
        print('*** Searching for objects ***')
        request = self.factory.get(reverse('transfer-list'), {'updated_since': self.updated_time})
        response = TransferViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertTrue(len(response.data) >= 1, "No search results")

    def process_view(self):
        print('*** Test TransferProcessView ***')
        with transformer_vcr.use_cassette('process_transfers.json'):
            request = self.factory.post(reverse('process'))
            response = ProcessTransfersView.as_view()(request)
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")

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
        self.process_view()
        self.schema()
        self.health_check()
