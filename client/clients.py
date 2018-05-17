from asnake.client import ASnakeClient
from electronbonder.client import ElectronBond
import json
import logging
from os.path import join
from structlog import wrap_logger
from uuid import uuid4

from aurora_fetcher import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class AuroraClient(object):

    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.client = ElectronBond(
            baseurl=settings.AURORA['baseurl'],
            username=settings.AURORA['username'],
            password=settings.AURORA['password'],
        )
        if not self.client.authorize():
            self.log.error("Couldn't authenticate user credentials for Aurora")

    def get_data(self, url):
        self.log = self.log.bind(request_id=str(uuid4()))
        resp = self.client.get(url)
        if resp.status_code != 200:
            self.log.error("Error retrieving data from Aurora: {msg}".format(msg=resp.json()['detail']))
            return False
        self.log.debug("Object retrieved from Aurora", object=url)
        return resp.json()

    def update_data(self, url, data):
        self.log.debug("Object saved in Aurora", object=url)
        return True


class ArchivesSpaceClient(object):

    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.client = ASnakeClient(
            baseurl=settings.ARCHIVESSPACE['baseurl'],
            username=settings.ARCHIVESSPACE['username'],
            password=settings.ARCHIVESSPACE['password'],
        )
        if not self.client.authorize():
            self.log.error(
                "Couldn't authenticate user credentials for ArchivesSpace",
                object=settings.ARCHIVESSPACE['username'])
            return False
        self.repo_id = settings.ARCHIVESSPACE['repo_id']

    def save_data(self, data, type):
        self.log = self.log.bind(request_id=str(uuid4()))
        ENDPOINTS = {
            'component': 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id),
            'accession': 'repositories/{repo_id}/accessions'.format(repo_id=self.repo_id),
            'person': 'agents/people',
            'organization': 'agents/corporate_entities',
            'family': 'agents/families',
        }
        resp = self.client.post(ENDPOINTS[type], data=json.dumps(data))
        if resp.status_code != 200:
            self.log.error('Error creating object in ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
            return False
        self.log.debug("Object created in Archivesspace", object=resp.json()['uri'])
        return resp.json()['uri']

    def get_or_create(self, type, field, value, consumer_data):
        self.log = self.log.bind(request_id=str(uuid4()))
        TYPE_LIST = (
            ('family', 'agent_family'),
            ('organization', 'agent_corporate_entity'),
            ('person', 'agent_person'),
            ('component', 'archival_object'),
            ('grouping_component', 'archival_object'),
            ('accession', 'accession')
        )
        model_type = [t[1] for t in TYPE_LIST if t[0] == type][0]
        query = json.dumps({"query": {"field": field, "value": value, "jsonmodel_type": "field_query"}})
        resp = self.client.get('search', params={"page": 1, "type[]": model_type, "aq": query})
        if resp.status_code != 200:
            self.log.error('Error searching for agent: {msg}'.format(msg=resp.json()['error']))
            return False
        if len(resp.json()['results']) == 0:
            self.log.debug("No match for object found in ArchivesSpace", object=value)
            if self.save_data(consumer_data, type):
                return self.save_data(consumer_data, type)
        return resp.json()['results'][0]['uri']
