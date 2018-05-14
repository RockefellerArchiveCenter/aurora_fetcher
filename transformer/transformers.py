import iso8601
import json

from aurora_fetcher import settings
from transformer.models import ConsumerObject
from client.clients import ArchivesSpaceClient


class ArchivesSpaceDataTransformer(object):

    def __init__(self, data, type, source_object):
        self.data = data
        self.metadata = data['metadata']
        self.type = type
        self.source_object = source_object

    def run(self):
        if not getattr(self, 'transform_{}'.format(self.type))():
            print("Error transforming data")
            return False

        consumer_object = ConsumerObject.objects.create(
            consumer='archivesspace',
            type=self.type,
            source_object=self.source_object,
            data=self.consumer_data,
        )

        if not ArchivesSpaceClient().save_data(self.consumer_data, self.type):
            print("Error delivering data")
            return False

    ####################################
    # Helper functions
    ####################################

    def resolve_agent_ref(self, agent_name):
        return "/agents/corporate_entities/1"

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

    def transform_linked_agents(self):
        linked_agents = []
        if 'source_organization' in self.data['metadata']:
            agent_ref = self.resolve_agent_ref(self.data['metadata']['source_organization'])
            linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
        if 'record_creators' in self.data['metadata']:
            for agent in self.data['metadata']['record_creators']:
                agent_ref = self.resolve_agent_ref(agent)
                linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
        return linked_agents

    def transform_rights(self):
        rights_statements = []
        for r in self.data['rights_statements']:
            statement = None
            rights_statements.append(statement)
        return rights_statements

    def transform_scopecontent(self, note_text):
        note = ""
        if len(note_text) > 0:
            note = {"jsonmodel_type": "note_multipart", "type": "scopecontent",
                    "publish": False, "subnotes": [
                        {"content": note_text, "publish": True,
                         "jsonmodel_type": "note_text"}]}
        return note

    ##################################
    # Main object transformations
    #################################

    def transform_component(self):
        defaults = {
            "publish": False, "level": "file", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            title = self.metadata['title']
            language = self.transform_langcode(self.metadata['language'])
            external_ids = self.transform_external_ids(self.data['url'])
            extents = self.transform_extents(
                {"bytes": self.metadata['payload_oxum'].split(".")[0],
                 "files": self.metadata['payload_oxum'].split(".")[1]})
            dates = self.transform_dates(self.metadata['date_start'], self.metadata['date_end'])
            scopecontent = self.transform_scopecontent(self.metadata['internal_sender_description'])
            langmaterial = self.transform_langnote(self.metadata['language'])
            repository_ref = {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])}
            resource_ref = {'ref': self.data['collection']}
            rights_statements = self.transform_rights()
            linked_agents = self.transform_linked_agents()

            self.consumer_data = {**defaults, "title": title, "language": language,
                "external_ids": external_ids, "extents": extents,
                "dates": dates, "rights_statements": rights_statements,
                "linked_agents": linked_agents, "resource": resource_ref,
                "repository": repository_ref, "notes": [scopecontent, langmaterial]}

            if 'parent' in self.data:
                parent_ref = {"ref": self.data['parent']}
                self.consumer_data = {**self.consumer_data, "parent": parent_ref}

            return True
        except Exception as e:
            print(e)
            return False
