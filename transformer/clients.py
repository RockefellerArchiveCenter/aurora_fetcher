from asnake.client import *
from electronbonder.client import *
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


class ArchivesSpaceClientError(Exception): pass


class UrsaMajorClientError(Exception): pass


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
            raise ArchivesSpaceClientError(
                "Couldn't authenticate user credentials for ArchivesSpace",
                object=settings.ARCHIVESSPACE['username'])
        self.repo_id = settings.ARCHIVESSPACE['repo_id']

    def create(self, data, type, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        ENDPOINTS = {
            'component': 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id),
            'accession': 'repositories/{repo_id}/accessions'.format(repo_id=self.repo_id),
            'person': 'agents/people',
            'organization': 'agents/corporate_entities',
            'family': 'agents/families',
        }
        resp = self.client.post(ENDPOINTS[type], data=json.dumps(data), *args, **kwargs)
        if resp.status_code != 200:
            self.log.error('Error creating object in ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
            raise ArchivesSpaceClientError('Error creating object in ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
        self.log.debug("Object created in Archivesspace", object=resp.json()['uri'])
        return resp.json()['uri']

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
        resp = self.client.get('search', params={"page": 1, "type[]": model_type, "aq": query})
        if resp.status_code != 200:
            self.log.error('Error searching for agent: {msg}'.format(msg=resp.json()['error']))
            raise ArchivesSpaceClientError('Error searching for agent: {msg}'.format(msg=resp.json()['error']))
        if len(resp.json()['results']) == 0:
            resp = self.client.get(endpoint, params={"all_ids": True, "modified_since": last_updated-120})
            if resp.status_code != 200:
                self.log.error('Error getting updated agents: {msg}'.format(msg=resp.json()['error']))
                raise ArchivesSpaceClientError('Error getting updated agents: {msg}'.format(msg=resp.json()['error']))
            for ref in resp.json():
                resp = self.client.get('{}/{}'.format(endpoint, ref))
                if resp.json()[field] == str(value):
                    return resp.json()['uri']
            self.log.debug("No match for object found in ArchivesSpace", object=value)
            return self.create(consumer_data, type)
        return resp.json()['results'][0]['uri']

    def retrieve(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        resp = self.client.get(url, *args, **kwargs)
        if resp.status_code != 200:
            self.log.error('Error retrieving object from ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
            raise ArchivesSpaceClientError('Error retrieving object from ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
        self.log.debug("Updated accessions retrieved from Archivesspace")
        return resp.json()


class UrsaMajorClient(object):

    def __init__(self):
        self.log = logger.bind(transaction_id=str(uuid4()))
        self.client = self.retry_session(retries=5)
        self.baseurl = settings.URSA_MAJOR['baseurl']

    # TODO move this to client library
    def retry_session(self, retries, session=None, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def retrieve(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        # TODO: move URL manipulation to client library
        url = urlparse(url)
        full_url = "/".join([self.baseurl.rstrip("/"), url.path.lstrip("/")])
        resp = self.client.get(full_url, *args, **kwargs)
        if resp.status_code != 200:
            self.log.error("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
            raise UrsaMajorClientError("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
        self.log.debug("Object retrieved from Ursa Major", object=url)
        return resp.json()

    def retrieve_paged(self, url, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        try:
            # TODO: move URL manipulation to client library
            full_url = "/".join([self.baseurl.rstrip("/"), url.lstrip("/")])
            resp = self.client.get_paged(full_url, *args, **kwargs)
            self.log.debug("List retrieved from Ursa Major", object=url)
            return resp
        except Exception as e:
            self.log.error("Error retrieving list from Ursa Major: {}".format(e))
            raise UrsaMajorClientError(e)

    def update(self, url, data, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        # TODO: move URL manipulation to client library
        url = urlparse(url)
        full_url = "/".join([self.baseurl.rstrip("/"), url.path.lstrip("/")])
        resp = self.client.put(full_url, data=json.dumps(data), headers={"Content-Type":"application/json"}, *args, **kwargs)
        if resp.status_code != 200:
            self.log.error("Error saving data in Ursa Major: {msg}".format(msg=resp.json()['detail']))
            raise UrsaMajorClientError("Error saving data in Ursa Major: {msg}".format(msg=resp.json()['detail']))
        self.log.debug("Object saved in Ursa Major", object=url)
        return resp.json()

    def find_bag_by_id(self, identifier, *args, **kwargs):
        self.log = self.log.bind(request_id=str(uuid4()))
        # TODO: move URL manipulation to client library
        full_url = "/".join([self.baseurl.rstrip("/"), 'bags/?id={}'.format(identifier)])
        object = self.client.get(full_url, *args, **kwargs)
        if object.status_code != 200:
            self.log.error("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
            raise UrsaMajorClientError("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
        bag = object.json()[0]
        object_url = bag['url']
        object_url = urlparse(object_url)
        full_url = "/".join([self.baseurl.rstrip("/"), object_url.path.lstrip("/")])
        resp = self.client.get(full_url, *args, **kwargs)
        if object.status_code != 200:
            self.log.error("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
            raise UrsaMajorClientError("Error retrieving data from Ursa Major: {msg}".format(msg=resp.json()['detail']))
        self.log.debug("Object retrieved from Ursa Major", object=identifier)
        return resp.json()
