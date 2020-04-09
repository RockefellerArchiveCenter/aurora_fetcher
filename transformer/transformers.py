import json
import time

from aquarius import settings
from odin.codecs import json_codec

from .clients import ArchivesSpaceClient
from .mappings import (SourceAccessionToArchivesSpaceAccession,
                       SourceAccessionToGroupingComponent,
                       SourceAgentToArchivesSpaceAgentCorporateEntity,
                       SourceAgentToArchivesSpaceAgentFamily,
                       SourceAgentToArchivesSpaceAgentPerson,
                       SourcePackageToDigitalObject,
                       SourceTransferToTransferComponent)
from .resources.source import (SourceAccession, SourceAgent, SourcePackage,
                               SourceTransfer)


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

    def transform_digital_object(self, data):
        from_obj = json_codec.loads(json.dumps(data), resource=SourcePackage)
        return json.loads(json_codec.dumps(SourcePackageToDigitalObject.apply(from_obj)))

    def transform_component(self, data, resource):
        data["resource"] = resource
        data["level"] = "file"
        from_obj = json_codec.loads(json.dumps(data), resource=SourceTransfer)
        return json.loads(json_codec.dumps(SourceTransferToTransferComponent.apply(from_obj)))

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
