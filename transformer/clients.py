from asnake.client import *
from electronbonder.client import *
from datetime import date
import json
import logging
from os.path import join
import requests
from structlog import wrap_logger
from uuid import uuid4
from urllib.parse import urljoin, urlparse
from urllib3.util.retry import Retry

from aquarius import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class ArchivesSpaceClient(object):

    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.client = ASnakeClient(
            baseurl=settings.ARCHIVESSPACE['baseurl'],
            username=settings.ARCHIVESSPACE['username'],
            password=settings.ARCHIVESSPACE['password'],
        )
        self.repo_id = settings.ARCHIVESSPACE['repo_id']
        if not self.client.authorize():
            self.log.error(
                "Couldn't authenticate user credentials for ArchivesSpace",
                object=settings.ARCHIVESSPACE['username'])
            return False

    def create(self, data, type, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        ENDPOINTS = {
            'component': 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id),
            'accession': 'repositories/{repo_id}/accessions'.format(repo_id=self.repo_id),
            'digital object': 'repositories/{repo_id}/digital_objects'.format(repo_id=self.repo_id),
            'person': 'agents/people',
            'organization': 'agents/corporate_entities',
            'family': 'agents/families',
        }
        try:
            resp = self.client.post(ENDPOINTS[type], data=json.dumps(data), *args, **kwargs)
            self.log.debug("Object created in Archivesspace", object=resp.json()['uri'])
            return resp.json()['uri']
        except Exception as e:
            self.log.error('Error creating object in ArchivesSpace: {}'.format(e))
            return False

    def update(self, uri, data, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            resp = self.client.post(uri, data=json.dumps(data), *args, **kwargs)
            self.log.debug("Object updated in Archivesspace", object=resp.json()['uri'])
            return resp.json()['uri']
        except Exception as e:
            self.log.error('Error updating object in ArchivesSpace: {}'.format(e))
            return False

    def get_or_create(self, type, field, value, last_updated, consumer_data):
        self.log = self.log.bind(request_id=str(uuid4()))
        TYPE_LIST = (
            ('family', 'agent_family', 'agents/families'),
            ('organization', 'agent_corporate_entity', 'agents/corporate_entities'),
            ('person', 'agent_person', 'agents/people'),
            ('component', 'archival_object', 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id)),
            ('grouping_component', 'archival_object', 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id)),
            ('accession', 'accession', 'repositories/{repo_id}/accessions'.format(repo_id=self.repo_id))
        )
        model_type = [t[1] for t in TYPE_LIST if t[0] == type][0]
        endpoint = [t[2] for t in TYPE_LIST if t[0] == type][0]
        query = json.dumps({"query": {"field": field, "value": value, "jsonmodel_type": "field_query"}})
        try:
            resp = self.client.get('search', params={"page": 1, "type[]": model_type, "aq": query})
            if len(resp.json()['results']) == 0:
                resp = self.client.get(endpoint, params={"all_ids": True, "modified_since": last_updated-120})
                for ref in resp.json():
                    resp = self.client.get('{}/{}'.format(endpoint, ref))
                    if resp.json()[field] == str(value):
                        return resp.json()['uri']
                self.log.debug("No match for object found in ArchivesSpace", object=value)
                return self.create(consumer_data, type)
            return resp.json()['results'][0]['uri']
        except Exception as e:
            self.log.error('Error finding or creating object in ArchivesSpace: {}'.format(e))
            return False

    def retrieve(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            resp = self.client.get(url, *args, **kwargs)
            self.log.debug("Updated accessions retrieved from Archivesspace")
            return resp.json()
        except Exception as e:
            self.log.error('Error retrieving object from ArchivesSpace: {}'.format(e))
            return False

    def next_accession_number(self):
        current_year = str(date.today().year)
        try:
            query = json.dumps({"query": {"field": "four_part_id", "value": current_year, "jsonmodel_type": "field_query"}})
            resp = self.client.get('search', params={"page": 1, "type[]": "accession", "sort": "four_part_id desc", "aq": query}).json()
            if resp.get('total_hits') < 1:
                return [current_year, "001"]
            else:
                if resp['results'][0]['identifier'].split("-")[0] == current_year:
                    id_1 = int(resp['results'][0]['identifier'].split("-")[1])
                    id_1 += 1
                    updated = str(id_1).zfill(3)
                    return [current_year, updated]
                else:
                    return [current_year, "001"]
        except Exception as e:
            self.log.error('Error retrieving next accession number from ArchivesSpace: {}'.format(e))
            return False


class UrsaMajorClient(object):

    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.client = ElectronBond(
             baseurl=settings.URSA_MAJOR['baseurl']
        )

    def retrieve(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            resp = self.client.get(url, *args, **kwargs)
            self.log.debug("Object retrieved from Ursa Major", object=url)
            return resp.json()
        except Exception as e:
            self.log.error("Error retrieving data from Ursa Major: {}".format(e))
            return False

    def retrieve_paged(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            resp = self.client.get_paged(url, *args, **kwargs)
            self.log.debug("List retrieved from Ursa Major", object=url)
            return resp
        except Exception as e:
            self.log.error("Error retrieving list from Ursa Major: {}".format(e))
            return False

    def update(self, url, data, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            resp = self.client.put(url, data=json.dumps(data), headers={"Content-Type":"application/json"}, *args, **kwargs)
            self.log.debug("Object saved in Ursa Major", object=url)
            return resp.json()
        except Exception as e:
            self.log.error("Error updating object in Ursa Major: {}".format(e))
            return False

    def find_bag_by_id(self, identifier, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            bag_resp = self.client.get("bags/?id={}".format(identifier), *args, **kwargs)
            bag_url = bag_resp.json()[0]['url']
            resp = self.client.get(bag_url, *args, **kwargs)
            self.log.debug("Object retrieved from Ursa Major", object=bag_url)
            return resp.json()
        except Exception as e:
            self.log.error("Error finding bag by id: {}".format(e))
            return False
