import odin

from .resources.archivesspace import (ArchivesSpaceAccession,
                                      ArchivesSpaceAgentCorporateEntity,
                                      ArchivesSpaceAgentFamily,
                                      ArchivesSpaceAgentPerson,
                                      ArchivesSpaceDate, ArchivesSpaceExtent,
                                      ArchivesSpaceExternalId,
                                      ArchivesSpaceLinkedAgent,
                                      ArchivesSpaceNameCorporateEntity,
                                      ArchivesSpaceNameFamily,
                                      ArchivesSpaceNamePerson,
                                      ArchivesSpaceRef,
                                      ArchivesSpaceRightsStatement)
from .resources.source import (SourceAccession, SourceAgent,
                               SourceRightsStatement)


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
        return [
            ArchivesSpaceExtent(number=extent_size, extent_type="bytes", portion="whole"),
            ArchivesSpaceExtent(number=extent_files, extent_type="files", portion="whole")
        ]

    @odin.map_field(from_field=("start_date", "end_date"), to_field="dates", to_list=True)
    def dates(self, date_start, date_end):
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

    @odin.map_list_field(from_field="rights_statements", to_field="rights_statements", to_list=True)
    def rights_statements(self, value):
        return [SourceRightsStatementToArchivesSpaceRightsStatement.apply(v) for v in value]

    @odin.map_list_field(from_field=("creators", "organization"), to_field="linked_agents", to_list=True)
    def linked_agents(self, creators, organization):
        data = []
        creators = [SourceAgentToArchivesSpaceAgent.apply(c) for c in creators]
        organization = [SourceAgentToArchivesSpaceAgentCorporateEntity.apply(organization)]
        for agent in creators + organization:
            agent_ref = self.aspace_client.get_or_create(
                agent['type'], 'title', agent['name'],
                self.transform_start_time, agent)
            data.append(ArchivesSpaceLinkedAgent(role="creator", ref=agent_ref))
        return data

    @odin.map_field(from_field="resource", to_field="related_resources", to_list=True)
    def resource(self, value):
        return [ArchivesSpaceRef(ref=value)]
    #
    # @odin.map_field(to_field="repository")
    # def repository(self):
    #     return ArchivesSpaceRef(ref="/repositories/{}".format(settings.ARCHIVESSPACE['repo_id']))
    #
    #     for n, segment in enumerate(accession_number):
    #         consumer_data = {
    #             **consumer_data,
    #             "id_{}".format(n): accession_number[n]}
