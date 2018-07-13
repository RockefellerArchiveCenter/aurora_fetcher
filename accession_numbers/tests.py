from datetime import date
import random
import time
import vcr

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from accession_numbers.cron import ArchivesSpaceAccessionNumbers
from accession_numbers.models import AccessionNumber
from accession_numbers.views import AccessionNumberViewSet, NextAccessionNumberView
from clients.clients import ArchivesSpaceClient

altair_vcr = vcr.VCR(
    serializer='json',
    cassette_library_dir='fixtures/cassettes',
    record_mode='new_episodes',
    match_on=['path', 'method'],
    filter_query_parameters=['username', 'password'],
    filter_headers=['Authorization', 'X-ArchivesSpace-Session'],
)


class AccessionNumberTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user('admin', 'aurora@example.com', 'adminpass')
        self.timestamp = 1516150945  # hardcoded to take advantage of VCR.py cassettes
        self.year = date.today().year
        self.accession_number_count = 10

    def create_accession_numbers(self):
        print('*** Creating new accession numbers ***')
        for n in range(self.accession_number_count):
            request = self.factory.post(
                reverse('accessionnumber-list'),
                {'segment_1': self.year, 'segment_2': str(n).zfill(3),
                 'segment_3': random.choice([None, '001']), 'segment_4': None},
                format='json')
            force_authenticate(request, user=self.user)
            response = AccessionNumberViewSet.as_view(actions={"post": "create"})(request)
            print('Created accession number {number}'.format(number=response.data['display_string']))
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(
            len(AccessionNumber.objects.all()), self.accession_number_count,
            "Incorrect number of accession numbers created")
        return AccessionNumber.objects.all()

    def archivesspace_client(self):
        with altair_vcr.use_cassette('archivesspace_client_test.json'):
            print('*** Testing ArchivesSpace client ***')
            client = ArchivesSpaceClient()
            self.assertIsNot(False, client.get_updated_accessions(last_crawl_time=self.timestamp))
            print("Got updated accessions from ArchivesSpace")
            self.assertIsNot(False, client.get_deleted_accessions(last_crawl_time=self.timestamp))
            print("Got deleted accessions from ArchivesSpace")
            self.assertIsNot(False, client.get_accession(13))
            print("Got random accession from ArchivesSpace")

    def update_from_archivesspace(self):
        with altair_vcr.use_cassette('archivesspace_update.json'):
            self.assertIsNot(False, ArchivesSpaceAccessionNumbers().do(
                last_crawl_time=self.timestamp),
                "Getting updated accession numbers from ArchivesSpace failed")
            print("ArchivesSpace update routine ran successfully")

    def get_all_accession_numbers(self):
        print('*** Getting all accession numbers ***')
        request = self.factory.get(reverse('accessionnumber-list'), format='json')
        force_authenticate(request, user=self.user)
        response = AccessionNumberViewSet.as_view(actions={"get": "list"})(request)
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(
            response.data['count'], len(AccessionNumber.objects.all()),
            "Number of accession numbers doesn't match what was returned")

    def get_individual_accession_number(self):
        print('*** Getting individual accession numbers ***')
        for accession_number in AccessionNumber.objects.all():
            request = self.factory.get(
                reverse('accessionnumber-detail', kwargs={'pk': accession_number.pk}),
                format='json')
            force_authenticate(request, user=self.user)
            response = AccessionNumberViewSet.as_view(actions={"get": "retrieve"})(request, pk=accession_number.pk)
            print('Getting accession number {string}'.format(string=response.data['display_string']))
            self.assertEqual(response.status_code, 200, "Wrong HTTP code")
            self.assertTrue(
                str(accession_number.pk) in response.data['url'],
                "Got the wrong accession number")

    def get_next_accession_number(self):
        print('*** Getting next accession number ***')
        # adding letter to segment_2 to cover this edge case
        accession_number = AccessionNumber.objects.last()
        accession_number.segment_2 = str(self.accession_number_count).zfill(2)+"B"
        accession_number.save()
        request = self.factory.get(reverse('next-accession'), format='json')
        force_authenticate(request, user=self.user)
        response = NextAccessionNumberView.as_view()(request)
        print('Getting next accession number: {}'.format(response.data['display_string']))
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(
            str(self.year), response.data['segment_1'],
            "Did not get the next accession number for the current year")

        test_year = self.year-random.randint(1, 40)
        request = self.factory.get(reverse('next-accession'), {'year': str(test_year)}, format='json')
        force_authenticate(request, user=self.user)
        response = NextAccessionNumberView.as_view()(request, {'year': str(test_year)})
        print('Getting next accession number for {}'.format(test_year))
        self.assertEqual(response.status_code, 200, "Wrong HTTP code")
        self.assertEqual(
            str(test_year), response.data['segment_1'],
            "Did not get the next accession number for {}".format(test_year))
        self.assertEqual(
            "001", response.data['segment_2'],
            "Segment_2 was not equal to 001")

    def test_accession_numbers(self):
        self.accession_numbers = self.create_accession_numbers()
        self.archivesspace_client()
        self.update_from_archivesspace()
        self.get_all_accession_numbers()
        self.get_individual_accession_number()
        self.get_next_accession_number()
