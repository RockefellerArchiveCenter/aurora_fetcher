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

    def get_object(self, url):
        self.log.bind(request_id=str(uuid4()), object=identifier)
        resp = self.client.get(url)
        if resp.status_code != 200:
            self.log.error("Error retrieving object from Aurora: {msg}".format(msg=resp.json()['detail']))
            return False
        self.log.debug("Object retrieved from Aurora")
        return resp.json()
