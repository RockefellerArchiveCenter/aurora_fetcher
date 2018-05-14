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
            'agent': 'agents'
        }
        resp = self.client.post(ENDPOINTS[type], data=json.dumps(data))
        if resp.status_code != 200:
            self.log.error('Error creating Component in ArchivesSpace: {msg}'.format(msg=resp.json()['error']))
            return False
        self.log.debug("Component created in Archivesspace", object=resp.json()['uri'])
        return resp.json()['uri']
