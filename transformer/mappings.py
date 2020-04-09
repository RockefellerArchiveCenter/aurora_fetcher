import odin
from iso639 import languages as langz

from .resources.archivesspace import (ArchivesSpaceAccession,
                                      ArchivesSpaceAgentCorporateEntity,
                                      ArchivesSpaceAgentFamily,
                                      ArchivesSpaceAgentPerson,
                                      ArchivesSpaceArchivalObject,
                                      ArchivesSpaceDate,
                                      ArchivesSpaceDigitalObject,
                                      ArchivesSpaceExtent,
                                      ArchivesSpaceExternalId,
                                      ArchivesSpaceFileVersion,
                                      ArchivesSpaceNameCorporateEntity,
                                      ArchivesSpaceNameFamily,
                                      ArchivesSpaceNamePerson,
                                      ArchivesSpaceNote, ArchivesSpaceRef,
                                      ArchivesSpaceRightsStatement,
                                      ArchivesSpaceSubnote)
from .resources.source import (SourceAccession, SourceAgent, SourcePackage,
                               SourceRightsStatement, SourceTransfer)


def map_dates(date_start, date_end):
    if date_start > date_end:
        expression = '{} - {}'.format(
            date_start.strftime("%Y %B %e"),
            date_end.strftime("%Y %B %e"))
        return [ArchivesSpaceDate(
            expression=expression, begin=date_start, end=date_end,
            date_type="inclusive", label="creation")]
    else:
        expression = date_start.strftime("%Y %B %e")
        return [ArchivesSpaceDate(
            expression=expression, begin=date_start,
            date_type="single", label="creation")]


def map_extents(extent_size, extent_files):
    return [
        ArchivesSpaceExtent(number=extent_size, extent_type="bytes", portion="whole"),
        ArchivesSpaceExtent(number=extent_files, extent_type="files", portion="whole")
    ]


def map_note_multipart(text, type):
    if len(text) > 0:
        return ArchivesSpaceNote(
            jsonmodel_type="note_multipart", type=type,
            subnotes=[ArchivesSpaceSubnote(content=text, jsonmodel_type="note_text")])


class SourceAgentToArchivesSpaceAgentFamily(odin.Mapping):
    from_obj = SourceAgent
    to_obj = ArchivesSpaceAgentFamily

    @odin.map_field(from_field="name", to_field="names", to_list=True)
    def name(self, value):
        return [ArchivesSpaceNameFamily(family_name=value)]


class SourceAgentToArchivesSpaceAgentPerson(odin.Mapping):
    from_obj = SourceAgent
    to_obj = ArchivesSpaceAgentPerson

    @odin.map_field(from_field="name", to_field="names", to_list=True)
    def name(self, value):
        if ', ' in value:
            name = value.rsplit(', ', 1)
        elif ' ' in value:
            name = value.rsplit(' ', 1)[::-1]
        else:
            name = [value, '']
        return [ArchivesSpaceNamePerson(primary_name=name[0], rest_of_name=name[1], name_order="inverted")]


class SourceAgentToArchivesSpaceAgentCorporateEntity(odin.Mapping):
    from_obj = SourceAgent
    to_obj = ArchivesSpaceAgentCorporateEntity

    @odin.map_field(from_field="name", to_field="names", to_list=True)
    def name(self, value):
        return [ArchivesSpaceNameCorporateEntity(primary_name=value)]


class SourceAgentToArchivesSpaceAgent(object):
    MAPPINGS = {
        "person": SourceAgentToArchivesSpaceAgentPerson,
        "organization": SourceAgentToArchivesSpaceAgentCorporateEntity,
        "family": SourceAgentToArchivesSpaceAgentFamily,
    }

    def apply(self, agent):
        return self.MAPPINGS[agent["type"].apply(agent)]


class SourceRightsStatementToArchivesSpaceRightsStatement(odin.Mapping):
    from_obj = SourceRightsStatement
    to_obj = ArchivesSpaceRightsStatement
    # TODO: finish


class SourceAccessionToArchivesSpaceAccession(odin.Mapping):
    from_obj = SourceAccession
    to_obj = ArchivesSpaceAccession

    mappings = (
        ("description", None, "content_description"),
        ("acquisition_type", None, "acquisition_type"),
        ("use_restrictions", None, "use_restrictions_note"),
        ("access_restrictions", None, "access_restrictions_note"),
        ("accession_date", None, "accession_date"),
        ("title", None, "title")
    )

    @odin.map_field(from_field="url", to_field="external_ids", to_list=True)
    def url(self, value):
        return [ArchivesSpaceExternalId(external_id=value, source="aurora")]

    @odin.map_field(from_field=("extent_size", "extent_files"), to_field="extents", to_list=True)
    def extents(self, extent_size, extent_files):
        return map_extents(extent_size, extent_files)

    @odin.map_field(from_field=("start_date", "end_date"), to_field="dates", to_list=True)
    def dates(self, date_start, date_end):
        return map_dates(date_start, date_end)

    @odin.map_list_field(from_field="rights_statements", to_field="rights_statements", to_list=True)
    def rights_statements(self, value):
        return [SourceRightsStatementToArchivesSpaceRightsStatement.apply(v) for v in value]

    @odin.map_list_field(from_field=("creators", "organization"), to_field="linked_agents", to_list=True)
    def linked_agents(self, creators, organization):
        data = []
        creators = [SourceAgentToArchivesSpaceAgent.apply(c) for c in creators]
        organization = [SourceAgentToArchivesSpaceAgentCorporateEntity.apply(organization)]
        # TODO: sort this out
        # for agent in creators + organization:
        #     agent_ref = self.aspace_client.get_or_create(
        #         agent['type'], 'title', agent['name'],
        #         self.transform_start_time, agent)
        #     data.append(ArchivesSpaceLinkedAgent(role="creator", ref=agent_ref))
        return data

    @odin.map_field(from_field="resource", to_field="related_resources", to_list=True)
    def resource(self, value):
        return [ArchivesSpaceRef(ref=value)]

    @odin.map_field(from_field="accession_number", to_field=("id_0", "id_1"))
    def accession_number(self, accession_number):
        id_0, id_1 = accession_number
        return id_0, id_1


class SourceAccessionToGroupingComponent(odin.Mapping):
    from_obj = SourceAccession
    to_obj = ArchivesSpaceArchivalObject

    mappings = (
        ("title", None, "title"),
        ("language", None, "language"),
    )

    @odin.map_field(from_field="url", to_field="external_ids", to_list=True)
    def url(self, value):
        return [ArchivesSpaceExternalId(external_id=value, source="aurora")]

    @odin.map_field(from_field=("extent_size", "extent_files"), to_field="extents", to_list=True)
    def extents(self, extent_size, extent_files):
        return map_extents(extent_size, extent_files)

    @odin.map_field(from_field=("start_date", "end_date"), to_field="dates", to_list=True)
    def dates(self, date_start, date_end):
        return map_dates(date_start, date_end)

    @odin.map_list_field(from_field="rights_statements", to_field="rights_statements", to_list=True)
    def rights_statements(self, value):
        return [SourceRightsStatementToArchivesSpaceRightsStatement.apply(v) for v in value]

    @odin.map_list_field(from_field=("creators", "organization"), to_field="linked_agents", to_list=True)
    def linked_agents(self, creators, organization):
        data = []
        data += [SourceAgentToArchivesSpaceAgent.apply(c) for c in creators]
        data += [SourceAgentToArchivesSpaceAgentCorporateEntity.apply(organization)]
        # TODO: sort this out
        # for agent in creators + organization:
        #     agent_ref = self.aspace_client.get_or_create(
        #         agent['type'], 'title', agent['name'],
        #         self.transform_start_time, agent)
        #     data.append(ArchivesSpaceLinkedAgent(role="creator", ref=agent_ref))
        return data

    @odin.map_field(from_field="resource", to_field="related_resources", to_list=True)
    def resource(self, value):
        return [ArchivesSpaceRef(ref=value)]

    @odin.map_list_field(
        from_field=("access_restrictions", "use_restrictions", "description", "appraisal_note", "language"),
        to_field="notes", to_list=True)
    def notes(self, access_restrictions, use_restrictions, description, appraisal_note, languages):
        data = []
        language = "multiple languages" if (len(languages) > 1) else langz.get(part2b=languages[0]).name
        data.append(ArchivesSpaceNote(
            jsonmodel_type="note_singlepart", type="langmaterial", publish=False,
            content=["Materials are in {}".format(language)]))
        for text, type in [
                (access_restrictions, "accessrestrict"),
                (use_restrictions, "userestrict"),
                (description, "scopecontent"),
                (appraisal_note, "general_note")]:
            if text:
                data.append(map_note_multipart(text, type))
        return data


class SourceTransferToTransferComponent(odin.Mapping):
    from_obj = SourceTransfer
    to_obj = ArchivesSpaceArchivalObject

    mappings = (
        ("title", None, "title"),
    )

    @odin.map_field(from_field="url", to_field="external_ids", to_list=True)
    def url(self, value):
        return [ArchivesSpaceExternalId(external_id=value, source="aurora")]

    @odin.map_field(from_field="metadata", to_field="language")
    def language(self, value):
        return 'mul' if len(value.language) > 1 else value[0]

    @odin.map_field(from_field="metadata", to_field="extents", to_list=True)
    def extents(self, value):
        extent_size, extent_files = value.payload_oxum.split(".")
        return map_extents(extent_size, extent_files)

    @odin.map_field(from_field="metadata", to_field="dates")
    def dates(self, value):
        return map_dates(value.date_start, value.date_end)

    @odin.map_list_field(from_field="rights_statements", to_field="rights_statements", to_list=True)
    def rights_statements(self, value):
        return [SourceRightsStatementToArchivesSpaceRightsStatement.apply(v) for v in value]

    @odin.map_list_field(from_field="metadata", to_field="linked_agents", to_list=True)
    def linked_agents(self, value):
        data = []
        data += [SourceAgentToArchivesSpaceAgent.apply(c) for c in value.record_creators]
        data += [SourceAgentToArchivesSpaceAgentCorporateEntity.apply(value.source_organization)]
        # TODO: sort this out
        # for agent in creators + organization:
        #     agent_ref = self.aspace_client.get_or_create(
        #         agent['type'], 'title', agent['name'],
        #         self.transform_start_time, agent)
        #     data.append(ArchivesSpaceLinkedAgent(role="creator", ref=agent_ref))
        return data

    @odin.map_field(from_field="resource", to_field="resource")
    def resource(self, value):
        return {"ref": value}

    @odin.map_list_field(
        from_field="metadata",
        to_field="notes", to_list=True)
    def notes(self, value):
        data = []
        language = "multiple languages" if (len(value.language) > 1) else langz.get(part2b=value.language[0]).name
        data.append(ArchivesSpaceNote(
            jsonmodel_type="note_singlepart", type="langmaterial", publish=False,
            content=["Materials are in {}".format(language)]))
        if value.internal_sender_description:
            data.append(map_note_multipart(value.internal_sender_description, "scopecontent"))
        return data

    @odin.map_field(from_field="archivesspace_parent_identifier", to_field="parent")
    def parent(self, value):
        if value:
            return {"ref": value}


class SourcePackageToDigitalObject(odin.Mapping):
    from_obj = SourcePackage
    to_obj = ArchivesSpaceDigitalObject

    def extract_id(self, uri):
        return uri.split("/")[-1]

    @odin.map_field(from_field="fedora_uri", to_field="title")
    def title(self, value):
        return self.extract_id(value)

    @odin.map_field(from_field="fedora_uri", to_field="digital_object_id")
    def digital_object_id(self, value):
        return self.extract_id(value)

    @odin.map_field(from_field=("fedora_uri", "use_statement"), to_field="file_versions", to_list=True)
    def file_versions(self, fedora_uri, use_statement):
        return [ArchivesSpaceFileVersion(file_uri=fedora_uri, use_statement=use_statement)]
