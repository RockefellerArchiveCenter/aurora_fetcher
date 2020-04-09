import odin
from aquarius import settings

from . import resource_configs


"""Lays out the ArchivesSpace resources and their fields.
Defaults and choices chosen from resource_configs.py are included here."""


class ArchivesSpaceAncestor(odin.Resource):
    """Indicates the fields included in an AS ancestor resource."""
    ref = odin.StringField()
    level = odin.StringField(choices=resource_configs.LEVEL_CHOICES)


class ArchivesSpaceRef(odin.Resource):
    """Indicates the fields included in an AS ref resource."""
    ref = odin.StringField()


class ArchivesSpaceDate(odin.Resource):
    """Indicates the fields included in an AS date resource."""
    expression = odin.StringField(null=True)
    begin = odin.StringField(null=True)
    end = odin.StringField(null=True)
    date_type = odin.StringField(choices=resource_configs.DATE_TYPE_CHOICES)
    label = odin.StringField(choices=resource_configs.DATE_LABEL_CHOICES)


class ArchivesSpaceExtent(odin.Resource):
    """Indicates the fields included in an AS extent resource."""
    number = odin.StringField()
    container_summary = odin.StringField(null=True)
    portion = odin.StringField(choices=(('whole', 'Whole'), ('part', 'Part')))
    extent_type = odin.StringField(
        choices=resource_configs.EXTENT_TYPE_CHOICES)


class ArchivesSpaceExternalId(odin.Resource):
    """Indicates the fields included in an AS external id resource."""
    external_id = odin.StringField()
    source = odin.StringField()


class ArchivesSpaceLinkedAgent(odin.Resource):
    """Indicates the fields included in an AS linked agent resource."""
    role = odin.StringField(choices=resource_configs.AGENT_ROLE_CHOICES)
    relator = odin.StringField(
        choices=resource_configs.AGENT_RELATOR_CHOICES,
        null=True)
    ref = odin.StringField()


class ArchivesSpaceNameBase(odin.Resource):
    """Indicates the fields included in an AS name resource.

    Used in Family, Corporate Entity, and Personal name resources."""
    rules = odin.StringField(default="dacs")
    source = odin.StringField(default="local")


class ArchivesSpaceNameCorporateEntity(ArchivesSpaceNameBase):
    """Indicates the fields included in an AS corporate entity name resource."""
    primary_name = odin.StringField()


class ArchivesSpaceNameFamily(ArchivesSpaceNameBase):
    """Indicates the fields included in an AS family name resource."""
    family_name = odin.StringField()


class ArchivesSpaceNamePerson(ArchivesSpaceNameBase):
    primary_name = odin.StringField()
    rest_of_name = odin.StringField(null=True)
    name_order = odin.StringField(
        choices=(('direct', 'Direct'), ('inverted', 'Inverted')))


class ArchivesSpaceSubnote(odin.Resource):
    """Indicates the fields included in an AS subnote resource."""
    jsonmodel_type = odin.StringField()
    publish = odin.BooleanField(default=False)
    content = odin.StringField(null=True)
    items = odin.StringField(null=True)


class ArchivesSpaceNote(odin.Resource):
    """Indicates the fields included in an AS note resource."""
    publish = odin.BooleanField(default=False)
    jsonmodel_type = odin.StringField()
    type = odin.StringField()
    label = odin.StringField(null=True)
    subnotes = odin.ArrayOf(ArchivesSpaceSubnote, null=True)
    content = odin.StringField(null=True)
    items = odin.StringField(null=True)


class ArchivesSpaceRightsStatementAct(odin.Resource):
    """Indicates the fields included in an AS rights statement act resource."""
    act_type = odin.StringField()
    start_date = odin.DateField()
    end_date = odin.DateField(null=True)
    restriction = odin.StringField()
    notes = odin.ArrayOf(ArchivesSpaceNote)


class ArchivesSpaceRightsStatement(odin.Resource):
    """Indicates the fields included in an AS rights statement resource."""
    determination_date = odin.DateField(null=True)
    rights_type = odin.StringField()
    start_date = odin.DateField()
    end_date = odin.DateField(null=True)
    status = odin.StringField(null=True)
    other_rights_basis = odin.StringField(null=True)
    jurisdiction = odin.StringField(null=True)
    notes = odin.ArrayOf(ArchivesSpaceNote)
    acts = odin.ArrayOf(ArchivesSpaceRightsStatementAct)


class ArchivesSpaceComponentBase(odin.Resource):
    """Indicates the fields included in an AS component resource. Sets the base fields of an AS component to be used in other
    resources."""
    class Meta:
        abstract = True

    COMPONENT_TYPES = (
        ('archival_object', 'Archival Object'),
        ('accession', 'Accession'),
    )

    dates = odin.ArrayOf(ArchivesSpaceDate)
    extents = odin.ArrayOf(ArchivesSpaceExtent)
    external_documents = odin.ArrayField(null=True)
    external_ids = odin.ArrayOf(ArchivesSpaceExternalId)
    instances = odin.ArrayField(null=True)
    jsonmodel_type = odin.StringField(choices=COMPONENT_TYPES)
    linked_agents = odin.ArrayOf(ArchivesSpaceLinkedAgent)
    linked_events = odin.ArrayField(null=True)
    notes = odin.ArrayOf(ArchivesSpaceNote)
    publish = odin.BooleanField(default=False)
    repository = odin.DictField(default={"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])})
    rights_statements = odin.ArrayOf(ArchivesSpaceRightsStatement)
    subjects = odin.ArrayField(null=True)
    title = odin.StringField(null=True)
    uri = odin.StringField()


class ArchivesSpaceArchivalObject(ArchivesSpaceComponentBase):
    """Indicates the fields included in an AS archival object resource."""
    language = odin.StringField(null=True)
    level = odin.StringField(choices=resource_configs.LEVEL_CHOICES)
    resource = odin.DictAs(ArchivesSpaceRef)
    parent = odin.DictField(null=True)


class ArchivesSpaceAccession(ArchivesSpaceComponentBase):
    """Documents the transfer of archival records to an archival repository."""
    accession_date = odin.StringField()
    access_restrictions_note = odin.StringField(null=True)
    acquisition_type = odin.StringField()
    content_description = odin.StringField()
    classifications = odin.ArrayField(null=True)
    deaccessions = odin.ArrayField(null=True)
    general_note = odin.StringField(null=True)
    id_0 = odin.StringField()
    id_1 = odin.StringField()
    related_accessions = odin.ArrayField(null=True)
    related_resources = odin.ArrayOf(ArchivesSpaceRef)
    use_restrictions_note = odin.StringField(null=True)


class ArchivesSpaceAgentCorporateEntity(odin.Resource):
    """Indicates the fields included in an AS agent corporate entity resource."""
    agent_type = odin.StringField(default="agent_corporate_entity")
    names = odin.ArrayOf(ArchivesSpaceNameCorporateEntity)


class ArchivesSpaceAgentFamily(odin.Resource):
    """Indicates the fields included in an AS agent family resource."""
    agent_type = odin.StringField(default="agent_family")
    names = odin.ArrayOf(ArchivesSpaceNameFamily)


class ArchivesSpaceAgentPerson(odin.Resource):
    """Indicates the fields included in an AS agent person resource."""
    agent_type = odin.StringField(default="agent_person")
    names = odin.ArrayOf(ArchivesSpaceNamePerson)


class ArchivesSpaceFileVersion(odin.Resource):
    file_uri = odin.StringField()
    use_statement = odin.StringField()


class ArchivesSpaceDigitalObject(odin.Resource):
    jsonmodel_type = odin.StringField(default="digital_object")
    publish = odin.BooleanField(default=False)
    title = odin.StringField()
    digital_object_id = odin.IntegerField()
    file_versions = odin.ArrayOf(ArchivesSpaceFileVersion)
    repository = odin.DictField(default={"ref": "/repositories/{}".format(settings.ARCHIVESSPACE['repo_id'])})
