import odin

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
    portion = odin.StringField(choices=(('whole', 'Whole'), ('part', 'Part'))),
    extent_type = odin.StringField(
        choices=resource_configs.EXTENT_TYPE_CHOICES)


class ArchivesSpaceExternalId(odin.Resource):
    """Indicates the fields included in an AS external id resource."""
    external_id = odin.StringField()
    source = odin.StringField()


class ArchivesSpaceSubcontainer(odin.Resource):
    """Indicates the fields included in an AS sub container resource."""
    indicator_2 = odin.StringField()
    type_2 = odin.StringField(choices=resource_configs.CONTAINER_TYPE_CHOICES)
    top_container = odin.DictAs(ArchivesSpaceRef)


class ArchivesSpaceInstance(odin.Resource):
    """Indicates the fields included in an AS instance resource."""
    instance_type = odin.StringField(
        choices=resource_configs.INSTANCE_TYPE_CHOICES)
    is_representative = odin.BooleanField()
    sub_container = odin.DictAs(ArchivesSpaceSubcontainer)


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
    content = odin.StringField(null=True)
    items = odin.StringField(null=True)


class ArchivesSpaceNote(odin.Resource):
    """Indicates the fields included in an AS note resource."""
    jsonmodel_type = odin.StringField()
    type = odin.StringField(null=True)
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


class ArchivesSpaceTerm(odin.Resource):
    """Indicates the fields included in an AS term resource."""
    term_type = odin.StringField(choices=resource_configs.TERM_TYPE_CHOICES)


class ArchivesSpaceSubject(odin.Resource):
    """Indicates the fields included in an AS subject resource."""
    title = odin.StringField()
    terms = odin.ArrayOf(ArchivesSpaceTerm)
    uri = odin.StringField()


class ArchivesSpaceComponentBase(odin.Resource):
    """Indicates the fields included in an AS component resource. Sets the base fields of an AS component to be used in other
    resources."""
    class Meta:
        abstract = True

    COMPONENT_TYPES = (
        ('archival_object', 'Archival Object'),
        ('resource', 'Resource')
    )

    publish = odin.BooleanField()
    title = odin.StringField(null=True)
    suppressed = odin.StringField()
    level = odin.StringField(choices=resource_configs.LEVEL_CHOICES)
    jsonmodel_type = odin.StringField(choices=COMPONENT_TYPES)
    external_ids = odin.ArrayOf(ArchivesSpaceExternalId)
    subjects = odin.ArrayOf(ArchivesSpaceRef)
    extents = odin.ArrayOf(ArchivesSpaceExtent)
    dates = odin.ArrayOf(ArchivesSpaceDate)
    rights_statements = odin.ArrayOf(ArchivesSpaceRightsStatement)
    linked_agents = odin.ArrayOf(ArchivesSpaceLinkedAgent)
    notes = odin.ArrayOf(ArchivesSpaceNote)
    uri = odin.StringField()


class ArchivesSpaceArchivalObject(ArchivesSpaceComponentBase):
    """Indicates the fields included in an AS archival object resource."""
    position = odin.IntegerField()
    ref_id = odin.StringField()
    component_id = odin.StringField(null=True)
    display_string = odin.StringField()
    language = odin.StringField(null=True)
    restrictions_apply = odin.BooleanField()
    ancestors = odin.ArrayOf(ArchivesSpaceAncestor)
    resource = odin.DictAs(ArchivesSpaceRef)
    parent = odin.DictAs(ArchivesSpaceRef, null=True)
    has_unpublished_ancestor = odin.BooleanField()
    instances = odin.ArrayOf(ArchivesSpaceInstance)


class ArchivesSpaceResource(ArchivesSpaceComponentBase):
    """Indicates the fields included in an AS resource resource."""
    restrictions = odin.BooleanField()
    ead_id = odin.StringField(null=True)
    finding_aid_title = odin.StringField(null=True)
    finding_aid_filing_title = odin.StringField(null=True)
    language = odin.StringField()
    id_0 = odin.StringField()
    id_1 = odin.StringField(null=True)
    id_0 = odin.StringField(null=True)
    tree = odin.DictAs(ArchivesSpaceRef)


# class ArchivesSpaceSubject(odin.Resource):
#     """Indicates the fields included in an AS subject resource."""
#     title = odin.StringField()
#     source = odin.StringField(choices=resource_configs.SUBJECT_SOURCE_CHOICES)
#     external_ids = odin.ArrayOf(ArchivesSpaceExternalId)
#     publish = odin.BooleanField()
#     terms = odin.ArrayOf(ArchivesSpaceSubject)
#     uri = odin.StringField()


class ArchivesSpaceAccession(odin.Resource):
    id_0 = odin.StringField()
    id_1 = odin.StringField()
    id_2 = odin.StringField(null=True)
    id_3 = odin.StringField(null=True)
    publish = odin.BooleanField(default=False)
    jsonmodel_type = odin.StringField(default="accession")
    accession_date = odin.StringField()
    access_restrictions_note = odin.StringField(null=True)
    use_restrictions_note = odin.StringField(null=True)
    general_note = odin.StringField(null=True)
    acquisition_type = odin.StringField()
    content_description = odin.StringField()
    linked_events = odin.ArrayField(null=True)
    external_documents = odin.ArrayField(null=True)
    instances = odin.ArrayField(null=True)
    subjects = odin.ArrayField(null=True)
    classifications = odin.ArrayField(null=True)
    related_accessions = odin.ArrayField(null=True)
    deaccessions = odin.ArrayField(null=True)
    title = odin.StringField()
    external_ids = odin.ArrayOf(ArchivesSpaceExternalId)
    extents = odin.ArrayOf(ArchivesSpaceExtent)
    dates = odin.ArrayOf(ArchivesSpaceDate)
    rights_statements = odin.ArrayOf(ArchivesSpaceRightsStatement)
    linked_agents = odin.ArrayOf(ArchivesSpaceLinkedAgent)
    related_resources = odin.ArrayOf(ArchivesSpaceRef)
    repository = odin.DictField()


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
