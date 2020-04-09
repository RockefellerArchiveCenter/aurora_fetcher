import json
import time

from aquarius import settings
from odin.codecs import json_codec

from .clients import ArchivesSpaceClient
from .mappings import (SourceAccessionToArchivesSpaceAccession,
                       SourceAccessionToGroupingComponent,
                       SourceAgentToArchivesSpaceAgentCorporateEntity,
                       SourceAgentToArchivesSpaceAgentFamily,
                       SourceAgentToArchivesSpaceAgentPerson)
from .resources.source import SourceAccession, SourceAgent


class TransformError(Exception):
    pass


class DataTransformer:
    def __init__(self, aspace_client=None):
        self.aspace_client = aspace_client if aspace_client else \
            ArchivesSpaceClient(
                settings.ARCHIVESSPACE['baseurl'],
                settings.ARCHIVESSPACE['username'],
                settings.ARCHIVESSPACE['password'],
                settings.ARCHIVESSPACE['repo_id'])
        self.transform_start_time = int(time.time())

    ####################################
    # Helper functions
    ####################################

    def transform_langcode(self, languages):
        return 'mul' if len(languages) > 1 else languages[0]

    def transform_linked_agents(self, agents):
        linked_agents = []
        for agent in agents:
            # TODO: call transform here
            consumer_data = self.transform_agent(agent)
            agent_ref = self.aspace_client.get_or_create(
                agent['type'], 'title', agent['name'],
                self.transform_start_time, consumer_data)
            linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
        return linked_agents

    def transform_rights_acts(self, rights_granted):
        acts = []
        for granted in rights_granted:
            act_data = {
                "act_type": granted['act'],
                "restriction": granted['restriction'],
                "start_date": granted['start_date'],
                "end_date": granted['end_date'],
            }
            if granted['note'] != "":
                act_data["notes"] = [
                    {"jsonmodel_type": "note_rights_statement_act",
                     "type": "additional_information", "content": [granted['note']]}]
            acts.append(act_data)
        return acts

    def transform_rights(self, statements):
        rights_statements = []
        for r in statements:
            statement = {
                "rights_type": r['rights_basis'].lower(),
                "start_date": r['start_date'],
                "end_date": r['end_date'],
                "acts": self.transform_rights_acts(r['rights_granted']),
                "external_documents": [],
                "linked_agents": [],
            }
            if r['note'] != "":
                statement['notes'] = [
                    {"jsonmodel_type": "note_rights_statement",
                     "type": "type_note", "content": [r['note']]}]
            field_keys = ["status", "determination_date", "license_terms"]
            for k in field_keys:
                if r.get(k):
                    statement[k] = r[k]
            if r.get('citation'):
                statement["statute_citation"] = r['citation']
            if r.get('other_rights_basis'):
                statement["other_rights_basis"] = r['other_rights_basis'].lower()
            if r.get('jurisdiction'):
                statement["jurisdiction"] = r['jurisdiction'].upper()
            rights_statements.append(statement)
        return rights_statements

    ##################################
    # Main object transformations
    #################################

    def transform_digital_object(self):
        data = self.package
        defaults = {"publish": False, "jsonmodel_type": "digital_object"}
        do_id = data.fedora_uri.split("/")[-1]
        try:
            return {
                **defaults,
                "title": do_id,
                "digital_object_id": do_id,
                "file_versions": [{
                    "file_uri": data.fedora_uri,
                    "use_statement": data.use_statement}],
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])}
            }
        except Exception as e:
            raise TransformError('Error transforming digital object: {}'.format(e))

    def transform_component(self):
        data = self.package.data['data']
        resource = self.package.accession_data['data']['resource']
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
                "resource": {'ref': resource},
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                "notes": [
                    self.transform_note_multipart(metadata['internal_sender_description'], "scopecontent"),
                    self.transform_langnote(metadata['language'])]}
            if data['archivesspace_parent_identifier']:
                consumer_data = {**consumer_data, "parent": {"ref": data['archivesspace_parent_identifier']}}
            return consumer_data
        except Exception as e:
            raise TransformError('Error transforming component: {}'.format(e))

    def transform_grouping_component(self, data):
        data["level"] = "recordgrp"
        # TODO: some handling of linked agents here
        from_obj = json_codec.loads(json.dumps(data), resource=SourceAccession)
        return json.loads(json_codec.dumps(SourceAccessionToGroupingComponent.apply(from_obj)))

    def transform_accession(self, data):
        data["accession_number"] = self.aspace_client.next_accession_number()
        # TODO: some handling of linked agents here
        from_obj = json_codec.loads(json.dumps(data), resource=SourceAccession)
        return json.loads(json_codec.dumps(SourceAccessionToArchivesSpaceAccession.apply(from_obj)))

    def transform_agent(self, data):
        MAPPINGS = {
            "person": SourceAgentToArchivesSpaceAgentPerson,
            "organization": SourceAgentToArchivesSpaceAgentCorporateEntity,
            "family": SourceAgentToArchivesSpaceAgentFamily,
        }
        mapping = MAPPINGS[data["type"]]
        from_obj = json_codec.loads(json.dumps(data), resource=SourceAgent)
        return json.loads(json_codec.dumps(mapping.apply(from_obj)))
