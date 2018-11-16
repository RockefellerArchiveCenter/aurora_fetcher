import iso8601
import json
from pycountry import languages as langz
import time

from aquarius import settings
from .clients import ArchivesSpaceClient


class TransformError(Exception): pass


class DataTransformer(object):
    def __init__(self, aspace_client=None):
        self.aspace_client = aspace_client if aspace_client else ArchivesSpaceClient()
        self.transform_start_time = int(time.time())

    ####################################
    # Helper functions
    ####################################

    def transform_dates(self, start, end):
        date_start = iso8601.parse_date(start)
        date_end = iso8601.parse_date(end)
        if date_end > date_start:
            # TODO: make get_date_expression a model method
            expression = '{} - {}'.format(
                date_start.strftime("%Y %B %e"),
                date_end.strftime("%Y %B %e"))
            return [{"expression": expression, "begin": date_start.strftime("%Y-%m-%d"), "end": date_end.strftime("%Y-%m-%d"), "date_type": "inclusive",
                    "label": "creation"}]
        else:
            expression = date_start.strftime("%Y %B %e")
            return [{"expression": expression, "begin": date_start.strftime("%Y-%m-%d"), "date_type": "single",
                    "label": "creation"}]

    def transform_extents(self, extent_values):
        return [{"number": v, "portion": "whole", "extent_type": k} for k, v in extent_values.items()]

    def transform_external_ids(self, identifier):
        return [{"external_id": identifier, "source": "aurora", "jsonmodel_type": "external_id"}]

    def transform_identifier_ref(self, data, key):
        for identifier in data.get(key, []):
            if identifier['source'] == 'archivesspace':
                return identifier['identifier']

    def transform_langcode(self, languages):
        return 'mul' if len(languages) > 1 else languages[0]

    def transform_langnote(self, languages):
        language = "multiple languages" if (len(languages)>1) else langz.get(alpha_3=languages[0]).name
        return {"jsonmodel_type": "note_singlepart", "type": "langmaterial",
                "publish": False, "content": ["Materials are in {}".format(language)]}

    def transform_linked_agents(self, agents):
        linked_agents = []
        for agent in agents:
            consumer_data = self.transform_agent(agent)
            agent_ref = self.aspace_client.get_or_create(
                agent['type'], 'title', agent['name'],
                self.transform_start_time, consumer_data)
            linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
        return linked_agents

    def transform_note_multipart(self, text, type):
        if len(text) > 0:
            return {"jsonmodel_type": "note_multipart", "type": type,
                      "publish": False, "subnotes": [
                        {"content": text, "publish": True,
                         "jsonmodel_type": "note_text"}]}
        return ""

    def transform_rights_acts(self, rights_granted):
        acts = []
        for granted in rights_granted:
            acts.append({
                "notes": [
                    {"jsonmodel_type": "note_rights_statement_act",
                     "type": "additional_information", "content": [granted['note']]}],
                "act_type": granted['act'],
                "restriction": granted['restriction'],
                "start_date": granted['start_date'],
                "end_date": granted['end_date'],
            })
        return acts

    def transform_rights(self, statements):
        rights_statements = []
        for r in statements:
            statement = {
                "rights_type": r['rights_basis'].lower(),
                "start_date": r['start_date'],
                "end_date": r['end_date'],
                "notes": [
                    {"jsonmodel_type": "note_rights_statement",
                     "type": "type_note", "content": [r['note']]}],
                "acts": self.transform_rights_acts(r['rights_granted']),
                "external_documents": [],
                "linked_agents": [],
            }
            field_keys = ["status", "determination_date", "license_terms",
                          "jurisdiction", "other_rights_basis"]
            for k in field_keys:
                if k in r:
                    statement[k] = r[k]
            if 'citation' in r:
                statement["statute_citation"] = r['citation']
            rights_statements.append(statement)
        return rights_statements

    ##################################
    # Main object transformations
    #################################

    def transform_digital_object(self, data):
        defaults = {"publish": False, "jsonmodel_type": "digital_object"}
        do_id = data.fedora_uri.split("/")[-1]
        try:
            return {
                **defaults,
                "title": do_id,
                "digital_object_id": do_id,
                "file_versions": [{
                    "file_uri": data.fedora_uri,
                    "use_statement": data.get_use_statement()}],
                "repository": {"ref": "/repositories/2"}
                }
        except Exception as e:
            raise TransformError('Error transforming digital object: {}'.format(e))

    def transform_component(self, data):
        metadata = data['metadata']
        defaults = {
            "publish": False, "level": "file", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            consumer_data = {
                **defaults,
                "title": metadata['title'],
                "language": self.transform_langcode(metadata['language']),
                "external_ids": self.transform_external_ids(data['url']),
                "extents": self.transform_extents(
                    {"bytes": metadata['payload_oxum'].split(".")[0],
                     "files": metadata['payload_oxum'].split(".")[1]}),
                "dates": self.transform_dates(metadata['date_start'], metadata['date_end']),
                "rights_statements": self.transform_rights(data['rights_statements']),
                "linked_agents": self.transform_linked_agents(
                    metadata['record_creators'] + [{"name": metadata['source_organization'], "type": "organization"}]),
                "resource": {'ref': self.resource},
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                "notes": [
                    self.transform_note_multipart(metadata['internal_sender_description'], "scopecontent"),
                    self.transform_langnote(metadata['language'])]}
            if self.parent:
                consumer_data = {**consumer_data, "parent": {"ref": self.parent}}
            return consumer_data
        except Exception as e:
            raise TransformError('Error transforming component: {}'.format(e))

    def transform_grouping_component(self, data):
        defaults = {
            "publish": False, "level": "recordgrp", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            consumer_data = {
                **defaults,
                "title": data['title'],
                "language": data['language'],
                "external_ids": self.transform_external_ids(data['url']),
                "extents": self.transform_extents(
                    {"bytes": str(data['extent_size']),
                     "files": str(data['extent_files'])}),
                "dates": self.transform_dates(data['start_date'], data['end_date']),
                "rights_statements": self.transform_rights(data['rights_statements']),
                "linked_agents": self.transform_linked_agents(
                    data['creators']+[{"name": data['organization'], "type": "organization"}]),
                "resource": {'ref': data['resource']},
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                "notes": [
                    self.transform_note_multipart(data['access_restrictions'], "accessrestrict"),
                    self.transform_note_multipart(data['use_restrictions'], "userestrict"),
                    self.transform_langnote([data['language']])
                    ]}
            if 'description' in data:
                consumer_data['notes'].append(self.transform_note_multipart(data['description'], "scopecontent"))
            if 'appraisal_note' in data:
                consumer_data['notes'].append(self.transform_note_multipart(data['appraisal_note'], "appraisal"))
            return consumer_data
        except Exception as e:
            raise TransformError('Error transforming grouping component: {}'.format(e))

    def transform_accession(self, data):
        accession_number = self.aspace_client.next_accession_number()
        defaults = {
            "publish": False, "linked_events": [], "jsonmodel_type": "accession",
            "external_documents": [], "instances": [], "subjects": [],
            "classifications": [], "related_accessions": [], "deaccessions": [],
            }
        try:
            consumer_data = {
                **defaults,
                "title": data['title'],
                "external_ids": self.transform_external_ids(data['url']),
                "extents": self.transform_extents(
                    {"bytes": str(data['extent_size']),
                     "files": str(data['extent_files'])}),
                "dates": self.transform_dates(data['start_date'], data['end_date']),
                "rights_statements": self.transform_rights(data['rights_statements']),
                "linked_agents": self.transform_linked_agents(
                    data['creators']+[{"name": data['organization'], "type": "organization"}]),
                "related_resources": [{'ref': data['resource']}],
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                "accession_date": data['accession_date'],
                "access_restrictions_note": data['access_restrictions'],
                "use_restrictions_note": data['use_restrictions'],
                "acquisition_type": data['acquisition_type'],
                "content_description": data['description']}

            for n, segment in enumerate(accession_number):
                consumer_data = {
                    **consumer_data,
                    "id_{}".format(n): accession_number[n]}
            return {**consumer_data, "general_note": data['appraisal_note']} if ('appraisal_note' in data) else consumer_data
        except Exception as e:
            raise TransformError('Error transforming accession: {}'.format(e))

    def transform_agent(self, data):
        try:
            if data['type'] == 'person':
                # Name in inverted order
                if ', ' in data['name']:
                    name = data['name'].rsplit(', ', 1)
                # Name in direct order
                else:
                    name = data['name'].rsplit(' ', 1).reverse()
                consumer_data = {
                    "agent_type": "agent_person",
                    "names": [{"primary_name": name[0], "rest_of_name": name[1],
                               "name_order": "inverted", "sort_name_auto_generate": True,
                               "source": "local", "rules": "dacs"}]}
            elif data['type'] == 'organization':
                consumer_data = {
                    "agent_type": "agent_corporate_entity",
                    "names": [{"primary_name": data["name"], "sort_name_auto_generate": True,
                               "source": "local", "rules": "dacs"}]}
            elif data['type'] == 'family':
                consumer_data = {
                    "agent_type": "agent_family",
                    "names": [{"family_name": data["name"], "sort_name_auto_generate": True,
                               "source": "local", "rules": "dacs"}]}
            return consumer_data
        except Exception as e:
            raise TransformError('Error transforming agent: {}'.format(e))
