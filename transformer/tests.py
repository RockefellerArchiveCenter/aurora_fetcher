import json
import random
import time
from os import listdir
from os.path import join
import vcr

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from aquarius import settings
from transformer.cron import ProcessAccessions, RetrieveFailed
from transformer.models import SourceObject, ConsumerObject, Identifier
from transformer.views import TransformViewSet, SourceObjectViewSet, ConsumerObjectViewSet
from clients import clients

transformer_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir='fixtures/cassettes',
    record_mode='once',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)


class TransformTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = Client()
        self.user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
        self.accession_data = []
        self.transfer_count = 0
        for file in listdir(join(settings.BASE_DIR, 'fixtures/data/')):
            with open(join(settings.BASE_DIR, 'fixtures/data/{}'.format(file)), 'r') as json_file:
                data = json.load(json_file)
                self.accession_data.append(data)
                self.transfer_count += len(data['transfers'])
        self.updated_time = int(time.time())-(24*3600) # this is the current time minus 24 hours

    def transform_accessions(self):
        print('*** Transforming accessions ***')
        with transformer_vcr.use_cassette('transform_accessions.json'):
            for accession in self.accession_data:
                request = self.factory.post(reverse('transform-list'), accession, format='json')
                force_authenticate(request, user=self.user)
                response = TransformViewSet.as_view(actions={"post": "create"})(request)
                print('Created accession {url}'.format(url=response.data['url']))
                self.assertEqual(response.status_code, 200, "Wrong HTTP code")
            self.assertEqual(len(self.accession_data), len(SourceObject.objects.all()))
            self.assertEqual(len(self.accession_data), len(ConsumerObject.objects.all()))
            self.assertEqual(len(self.accession_data), len(Identifier.objects.all()))
            for object in SourceObject.objects.all():
                self.assertEqual(object.type, 'accession')
            for object in ConsumerObject.objects.all():
                self.assertEqual(object.type, 'accession')

    def transform_components(self):
        print('*** Transforming components ***')
        with transformer_vcr.use_cassette('transform_components.json'):
            cron = ProcessAccessions().do()
            for component in SourceObject.objects.filter(type='component'):
                self.assertEqual(len(component.data['external_identifiers']), 1)
                self.assertEqual(len(component.data['parents']), 1)
                self.assertEqual(len(component.data['collections']), 1)
            self.assertEqual(len(ConsumerObject.objects.filter(type='component')), self.transfer_count+len(self.accession_data)) # account for grouping components
            self.assertEqual(len(SourceObject.objects.filter(type='component')), self.transfer_count)
            self.assertEqual(len(Identifier.objects.all()), len(ConsumerObject.objects.all()))

    def retrieve_failed(self):
        print('*** Retrieving failed accessions ***')
        with transformer_vcr.use_cassette('retrieve_failed.json'):
            cron = RetrieveFailed().do()
            self.assertIsNot(False, cron)
            self.assertEqual(len(Identifier.objects.all()), len(ConsumerObject.objects.all()))

    def search_objects(self):
        print('*** Searching for objects ***')
        for object_type in [('sourceobject-list', SourceObjectViewSet), ('consumerobject-list', ConsumerObjectViewSet)]:
            type_request = self.factory.get(reverse(object_type[0]), {'type': random.choice(['accession', 'component'])})
            updated_request = self.factory.get(reverse(object_type[0]), {'updated_since': self.updated_time})
            combined_request = self.factory.get(reverse(object_type[0]), {'type': random.choice(['accession', 'component']), 'updated_since': self.updated_time})
            for request in [type_request, updated_request, combined_request]:
                force_authenticate(request, user=self.user)
                response = getattr(object_type[1], 'as_view')(actions={"get": "list"})(request)
                self.assertEqual(response.status_code, 200, "Wrong HTTP code")
                self.assertTrue(len(response.data) >= 1, "No search results")

    def home_view(self):
        print('*** Getting home page ***')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def test_components(self):
        self.transform_accessions()
        self.transform_components()
        self.retrieve_failed()
        self.search_objects()
        self.home_view()
