import iso8601
import json

from aurora_fetcher import settings
from transformer.models import ConsumerObject, Identifier
from client.clients import ArchivesSpaceClient


class ArchivesSpaceDataTransformer(object):

    def __init__(self, data, type, source_object):
        self.data = data
        self.type = type
        self.source_object = source_object

    def run(self):
        try:
            getattr(self, 'transform_{}'.format(self.type))()
            as_identifier = ArchivesSpaceClient().save_data(self.consumer_data, self.type)
            consumer_object = ConsumerObject.objects.create(
                consumer='archivesspace',
                type=self.type,
                source_object=self.source_object,
                data=self.consumer_data,
            )
            identifier = Identifier.objects.create(
                source='archivesspace',
                identifier=as_identifier,
                consumer_object=consumer_object,
            )
            return True
        except Exception as e:
            print(e)
            return False

    ####################################
    # Helper functions
    ####################################

    def resolve_agent_ref(self, agent_name):
        return "/agents/corporate_entities/1"

    def transform_accession_number(self, number):
        return number.split(".")

    def transform_dates(self, start, end):
        date_start = iso8601.parse_date(start)
        date_end = iso8601.parse_date(end)
        if date_end > date_start:
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
        extents = []
        for k, v in extent_values.items():
            extent = {"number": v, "portion": "whole", "extent_type": k}
            extents.append(extent)
        return extents

    def transform_external_ids(self, identifier):
        return [{"external_id": identifier, "source": "aurora", "jsonmodel_type": "external_id"}]

    def transform_langcode(self, languages):
        langcode = "mul"
        if len(languages) == 1:
            langcode = languages[0]
        return langcode

    def transform_langnote(self, languages):
        language = "multiple languages"
        if len(languages) == 1:
            language = "English"
        return {"jsonmodel_type": "note_singlepart", "type": "langmaterial",
                "publish": False, "content": ["Materials are in {}".format(language)]}

    def transform_linked_agents(self, agent_names):
        linked_agents = []
        for agent in agent_names:
            agent_ref = self.resolve_agent_ref(agent)
            linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
        return linked_agents

    def transform_note_multipart(self, text, type):
        note = ""
        if len(text) > 0:
            note = {"jsonmodel_type": "note_multipart", "type": type,
                    "publish": False, "subnotes": [
                        {"content": text, "publish": True,
                         "jsonmodel_type": "note_text"}]}
        return note

    def transform_rights_acts(self, rights_granted):
        acts = []
        for granted in rights_granted:
            act = {
                "notes": [
                    {"jsonmodel_type": "note_rights_statement_act",
                     "type": "additional_information", "content": [granted['note']]}],
                "act_type": granted['act'],
                "restriction": granted['restriction'],
                "start_date": granted['start_date'],
                "end_date": granted['end_date'],
            }
            acts.append(act)
        return acts

    def transform_rights(self):
        rights_statements = []
        for r in self.data['rights_statements']:
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
            if 'status' in r:
                statement = {**statement, "status": r['status']}
            if 'determination_date' in r:
                statement = {**statement, "determination_date": r['determination_date']}
            if 'terms' in r:
                statement = {**statement, "license_terms": r['terms']}
            if 'citation' in r:
                statement = {**statement, "statute_citation": r['citation']}
            if 'jurisdiction' in r:
                statement = {**statement, "jurisdiction": r['jurisdiction'].upper()}
            if 'other_rights_basis' in r:
                statement = {**statement, "other_rights_basis": r['other_rights_basis'].lower()}
            rights_statements.append(statement)
        return rights_statements

    ##################################
    # Main object transformations
    #################################

    def transform_component(self):
        metadata = self.data['metadata']
        defaults = {
            "publish": False, "level": "file", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            self.consumer_data = {
                **defaults,
                "title": metadata['title'],
                "language": self.transform_langcode(metadata['language']),
                "external_ids": self.transform_external_ids(self.data['url']),
                "extents": self.transform_extents(
                    {"bytes": metadata['payload_oxum'].split(".")[0],
                     "files": metadata['payload_oxum'].split(".")[1]}),
                "dates": self.transform_dates(metadata['date_start'], metadata['date_end']),
                "rights_statements": self.transform_rights(),
                "linked_agents": self.transform_linked_agents(
                    metadata['record_creators'] + [metadata['source_organization']]),
                "resource": {'ref': self.data['collection']},
                "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                "notes": [
                    self.transform_note_multipart(metadata['internal_sender_description'], "scopecontent"),
                    self.transform_langnote(metadata['language'])]}
            if 'parent' in self.data:
                self.consumer_data = {**self.consumer_data, "parent": {"ref": self.data['parent']}}
            return True
        except Exception as e:
            print(e)
            return False

        def transform_accession(self):
            accession_number = self.transform_accession_number(self.data['accession_number'])
            defaults = {
                "publish": False, "linked_events": [], "jsonmodel_type": "accession",
                "external_documents": [], "instances": [], "subjects": [],
                "classifications": [], "related_accessions": [], "deaccessions": [],
                }
            try:
                self.consumer_data = {
                    **defaults,
                    "title": self.data['title'],
                    "external_ids": self.transform_external_ids(self.data['url']),
                    "extents": self.transform_extents(
                        {"bytes": self.data['extent_size'],
                         "files": self.data['extent_files']}),
                    "dates": self.transform_dates(self.data['start_date'], self.data['end_date']),
                    "rights_statements": self.transform_rights(),
                    "linked_agents": self.transform_linked_agents(self.data['creators']),
                    "related_resources": [{'ref': self.data['resource']}],
                    "repository": {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])},
                    "accession_date": self.data['accession_date'],
                    "access_restrictions_note": self.data['access_restrictions'],
                    "use_restrictions_note": self.data['use_restrictions'],
                    "acquisition_type": self.data['acquisition_type'],
                    "content_description": self.data['description']}

                for n, segment in enumerate(accession_number):
                    self.consumer_data = {
                        **self.consumer_data,
                        "id_{}".format(n): accession_number.get(n)}
                if 'appraisal_note' in self.data:
                    self.consumer_data = {**self.consumer_data, "general_note": self.data['appraisal_note']}
                return True
            except Exception as e:
                print(e)
                return False
