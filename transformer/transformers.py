from jq import jq
import json

from aurora_fetcher import settings
from transformer.models import ConsumerObject
from client.clients import ArchivesSpaceClient


class ArchivesSpaceDataTransformer(object):

    def __init__(self, data, type, source_object):
        self.data = data
        self.type = type
        self.source_object = source_object

    def run(self):
        if not getattr(self, 'transform_{}_data'.format(self.type))():
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

    def resolve_parent_ref(self, data):
        # parse identifier from data
        # look for this in existing SourceObjects
        # if it's not there, check AS
        return None

    def resolve_collection_ref(self, data):
        # parse identifier from data
        # look for this in existing SourceObjects
        # if it's not there, try ArchivesSpace
        return '/repositories/2/resources/1'

    def resolve_agent_ref(self, agent_name):
        # look for this in existing SourceObjects
        # if it's not there, try ArchivesSpace
        return '/agents/corporate_entities/1'

    def transform_rights(self, rights_statement):
        return None

    def transform_component_data(self):
        defaults = {
            "publish": False, "level": "file", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            title = jq(".metadata.title").transform(self.data)
            language = jq(
                '(if .metadata.language|length == 1 then\
                    .metadata.language[0] else "mul" end)').transform(self.data)
            external_ids = jq(
                '[{external_id: .url, source: "aurora",\
                    jsonmodel_type: "external_id"}]').transform(self.data)
            extents = jq(
                '[{number: .metadata.payload_oxum | split(".")[0],\
                    portion: "whole", extent_type: "bytes"},\
                  {number: .metadata.payload_oxum | split(".")[1],\
                    portion: "whole", extent_type: "files"}]').transform(self.data)
            dates = jq(
                '[{expression: "", begin: .metadata.date_start,\
                    "end": .metadata.date_end, date_type: "inclusive",\
                    label: "creation"}]').transform(self.data)
            scopecontent = jq(
                'if .metadata.internal_sender_description|length > 0 then\
                    {jsonmodel_type: "note_multipart", type: "scopecontent", publish: false,\
                        subnotes: [\
                            {content: .metadata.internal_sender_description,\
                            publish: true, jsonmodel_type: "note_text"}]}\
                else "" end').transform(self.data)
            langmaterial = jq(
                '{jsonmodel_type: "note_singlepart", type: "langmaterial", publish: false,\
                    content: [(if .metadata.language|length == 1 then\
                        "Materials are in English" else\
                        "Materials are in multiple languages" end)]}').transform(self.data)
            repository_ref = {"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])}
            resource_ref = {'ref': self.resolve_collection_ref(self.data)}

            rights_statements = []
            for r in self.data['rights_statements']:
                rights_statement = self.transform_rights(r)
                rights_statements.append(r)

            linked_agents = []
            if 'source_organization' in self.data['metadata']:
                agent_ref = self.resolve_agent_ref(self.data['metadata']['source_organization'])
                linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})
            if 'record_creators' in self.data['metadata']:
                for agent in self.data['metadata']['record_creators']:
                    agent_ref = self.resolve_agent_ref(agent)
                    linked_agents.append({"role": "creator", "terms": [], "ref": agent_ref})

            consumer_data = {**defaults, "title": title, "language": language,
                "external_ids": external_ids, "extents": extents,
                "dates": dates, "rights_statements": rights_statements,
                "linked_agents": linked_agents, "resource": resource_ref,
                "repository": repository_ref, "notes": [scopecontent, langmaterial]}

            if 'parent' in self.data:
                parent_ref = {"ref": self.resolve_parent_ref(self.data)}
                consumer_data = {**consumer_data, "parent_ref": parent_ref}

            self.consumer_data = consumer_data
            return True
        except Exception as e:
            print(e)
            return False
