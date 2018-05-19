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
from transformer.cron import ProcessAccessions
from transformer.models import SourceObject, ConsumerObject, Identifier
from transformer.views import TransformViewSet, SourceObjectViewSet, ConsumerObjectViewSet
from client import clients

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
        for file in listdir(join(settings.BASE_DIR, 'fixtures/data/')):
            with open(join(settings.BASE_DIR, 'fixtures/data/{}'.format(file)), 'r') as json_file:
                self.accession_data.append(json.load(json_file))
        self.updated_time = int(time.time())-(24*3600) # this is the current time minus 24 hours

    def transform_accessions(self):
        print('*** Transforming accessions ***')
        with transformer_vcr.use_cassette('trasnform_accessions.json'):
            for accession in self.accession_data:
                request = self.factory.post(reverse('transform-list'), accession, format='json')
                force_authenticate(request, user=self.user)
                response = TransformViewSet.as_view(actions={"post": "create"})(request)
                print('Updated source {name}'.format(name=response.data['url']))
                self.assertEqual(response.status_code, 200, "Wrong HTTP code")
                # correct number of SourceObject
                # correct number of ConsumerObject
                # correct type in SourceObject
                # correct type in ConsumerObject

    def transform_components(self):
        print('*** Transforming components ***')
        pass

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
                # self.assertTrue(len(response.data) >= 1, "No search results")

    def home_view(self):
        print('*** Getting home page ***')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")

    def unauthorized_user(self):
        print('*** Testing unauthenticated user ***')
        response = self.client.get(reverse('transform-list'))
        self.assertEqual(response.status_code, 401, "Wrong HTTP code")

    def test_components(self):
        self.transform_accessions()
        self.transform_components()
        self.search_objects()
        self.home_view()
        self.unauthorized_user()
