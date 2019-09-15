from asnake.client import ASnakeClient
from electronbonder.client import ElectronBond
from datetime import date
import json


class ArchivesSpaceClientError(Exception): pass
class ArchivesSpaceClientAccessionNumberError(Exception): pass
class UrsaMajorClientError(Exception): pass
class AuroraClientError(Exception): pass


class ArchivesSpaceClient(object):
    """Client to get and receive data from ArchivesSpace."""

    def __init__(self, baseurl, username, password, repo_id):
        self.client = ASnakeClient(baseurl=baseurl, username=username, password=password)
        self.repo_id = repo_id
        if not self.client.authorize():
            raise ArchivesSpaceClientError("Couldn't authenticate user credentials for ArchivesSpace")

    def create(self, data, type, *args, **kwargs):
        ENDPOINTS = {
            'component': 'repositories/{repo_id}/archival_objects'.format(repo_id=self.repo_id),
            'accession': 'repositories/{repo_id}/accessions'.format(repo_id=self.repo_id),
            'digital object': 'repositories/{repo_id}/digital_objects'.format(repo_id=self.repo_id),
            'person': 'agents/people',
            'organization': 'agents/corporate_entities',
            'family': 'agents/families',
        }
        resp = self.client.post(ENDPOINTS[type], data=json.dumps(data), *args, **kwargs)
        if resp.status_code == 200:
            return resp.json()['uri']
        else:
            if resp.json()['error'].get('id_0'):
                raise ArchivesSpaceClientAccessionNumberError(resp.json()['error'])
            else:
                raise ArchivesSpaceClientError(resp.json()['error'])

    def update(self, uri, data, *args, **kwargs):
        try:
            resp = self.client.post(uri, data=json.dumps(data), *args, **kwargs)
            if resp.status_code == 200:
                return resp.json()['uri']
            else:
                raise ArchivesSpaceClientError('Error updating object in ArchivesSpace: {}'.format(resp.json()['error']))
        except Exception as e:
            raise ArchivesSpaceClientError('Error updating object in ArchivesSpace: {}'.format(e))

    def get_or_create(self, type, field, value, last_updated, consumer_data):
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
                return self.create(consumer_data, type)
            return resp.json()['results'][0]['uri']
        except Exception as e:
            raise ArchivesSpaceClientError('Error finding or creating object in ArchivesSpace: {}'.format(e))

    def retrieve(self, url, *args, **kwargs):
        try:
            resp = self.client.get(url, *args, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise ArchivesSpaceClientError('Error retrieving object from ArchivesSpace: {}'.format(resp.json()['error']))
        except Exception as e:
            raise ArchivesSpaceClientError('Error retrieving object from ArchivesSpace: {}'.format(e))

    def next_accession_number(self):
        current_year = str(date.today().year)
        try:
            query = json.dumps({"query": {"field": "four_part_id", "value": current_year, "jsonmodel_type": "field_query"}})
            resp = self.client.get('search', params={"page": 1, "type[]": "accession", "sort": "identifier desc", "aq": query}).json()
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
            raise ArchivesSpaceClientError('Error retrieving next accession number from ArchivesSpace: {}'.format(e))


class UrsaMajorClient(object):
    """Client to get and receive data from UrsaMajor."""

    def __init__(self, baseurl):
        self.client = ElectronBond(baseurl=baseurl)

    def retrieve(self, url, *args, **kwargs):
        try:
            resp = self.client.get(url, *args, **kwargs)
            return resp.json()
        except Exception as e:
            raise UrsaMajorClientError("Error retrieving data from Ursa Major: {}".format(e))

    def retrieve_paged(self, url, *args, **kwargs):
        try:
            resp = self.client.get_paged(url, *args, **kwargs)
            return resp
        except Exception as e:
            raise UrsaMajorClientError("Error retrieving list from Ursa Major: {}".format(e))

    def update(self, url, data, *args, **kwargs):
        try:
            resp = self.client.put(url, data=json.dumps(data), headers={"Content-Type":"application/json"}, *args, **kwargs)
            return resp.json()
        except Exception as e:
            raise UrsaMajorClientError("Error updating object in Ursa Major: {}".format(e))

    def find_bag_by_id(self, identifier, *args, **kwargs):
        try:
            bag_resp = self.client.get("bags/", params={"id": identifier}).json()
            count = bag_resp.get('count')
            if count != 1:
                raise UrsaMajorClientError("Found {} bags matching id {}, expected 1".format(count, identifier))
            bag_url = bag_resp.get('results')[0]['url']
            resp = self.client.get(bag_url, *args, **kwargs).json()
            return resp
        except Exception as e:
            raise UrsaMajorClientError("Error finding bag by id: {}".format(e))


class AuroraClient:

    def __init__(self, baseurl, username, password):
        self.client = ElectronBond(baseurl=baseurl, username=username, password=password)
        if not self.client.authorize():
            raise AuroraClientError("Could not authorize {} in Aurora".format(username))

    def update(self, url, data, *args, **kwargs):
        try:
            resp = self.client.put(url, data=json.dumps(data), headers={"Content-Type":"application/json"}, *args, **kwargs)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            raise AuroraClientError("Error updating object in Aurora: {}".format(e))
