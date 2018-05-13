from jq import jq
import json


class DataTransformer(object):

    def get_parent_ref(self, data):
        # parse identifier from data
        # look for this in existing SourceObjects
        # if it's not there, check AS
        return None

    def get_collection_ref(self, data):
        # parse identifier from data
        # look for this in existing SourceObjects
        # if it's not there, try ArchivesSpace
        return '/repositories/2/resources/12144'

    def to_archivesspace(self, data):
        defaults = {
            "publish": False, "level": "file", "linked_events": [],
            "external_documents": [], "instances": [], "subjects": []
            }
        try:
            title = jq(".metadata.title").transform(data)
            language = jq(
                '(if .metadata.language|length == 1 then\
                    .metadata.language[0] else "mul" end)').transform(data)
            external_ids = jq(
                '[{external_id: .url, source: "aurora",\
                    jsonmodel_type: "external_id"}]').transform(data)
            extents = jq(
                '[{number: .metadata.payload_oxum | split(".")[0],\
                    portion: "whole", extent_type: "cubic_feet"},\
                  {number: .metadata.payload_oxum | split(".")[1],\
                    portion: "whole", extent_type: "files"}]').transform(data)
            dates = jq(
                '[{expression: "", begin: .metadata.date_start,\
                    "end": .metadata.date_end, date_type: "inclusive",\
                    label: "creation"}]').transform(data)
            rights_statements = []
            linked_agents = jq(
                '[{role: "creator", terms: [], ref: "/agents/corporate_entities/4891"},\
                  {role: "creator", terms: [], ref: "/agents/corporate_entities/27"}]').transform(data)
            scopecontent = jq(
                'if .metadata.internal_sender_description|length > 0 then\
                    {jsonmodel_type: "note_multipart", type: "scopecontent", publish: false,\
                        subnotes: [\
                            {content: .metadata.internal_sender_description,\
                            publish: true, jsonmodel_type: "note_text"}]}\
                else "" end').transform(data)
            langmaterial = jq(
                '{jsonmodel_type: "note_singlepart", type: "langmaterial", publish: false,\
                    content: [(if .metadata.language|length == 1 then\
                        "Materials are in English" else\
                        "Materials are in multiple languages" end)]}').transform(data)
            repository_ref = '{ref: "/repositories/%s"}' % settings.ARCHIVESSPACE['repo_id']
            resource_ref = '{ref: %s }' % self.get_collection_ref(data)

            data = {**defaults, "title": title, "language": language,
                    "external_ids": external_ids, "extents": extents,
                    "dates": dates, "rights_statements": rights_statements,
                    "notes": [scopecontent, langmaterial], "resource": resource_ref}
            if 'parent' in data:
                parent_ref = '{ref: "%s"}' % self.get_parent_ref(data)
                data = {**data, "parent_ref": parent_ref}
            self.log.debug("Data from Aurora transformed for ArchivesSpace", request_id=str(uuid4()))
            return json.dumps(data)
        except Exception as e:
            self.log.error("Error transforming data from Aurora to ArchivesSpace: {e}".format(e=e), request_id=str(uuid4()))
            return False

    def to_fedora(self, data):
        return True
