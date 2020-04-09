import odin


class SourceRightsActs(odin.Resource):
    act = odin.StringField()
    restriction = odin.StringField()
    start_date = odin.DateField()
    end_date = odin.DateField()
    note = odin.StringField(null=True)


class SourceRightsStatement(odin.Resource):
    rights_basis = odin.StringField()
    start_date = odin.DateField()
    end_date = odin.DateField()
    rights_granted = odin.ArrayOf(SourceRightsActs)
    external_documents = odin.ArrayField(null=True)
    linked_agents = odin.ArrayField(null=True)
    note = odin.StringField(null=True)
    status = odin.StringField(null=True)
    determination_date = odin.DateField(null=True)
    license_terms = odin.StringField(null=True)
    citation = odin.StringField(null=True)
    other_rights_basis = odin.StringField(null=True)
    jurisdiction = odin.StringField(null=True)


class SourceMetadata(odin.Resource):
    date_end = odin.DateField()
    date_start = odin.DateField()
    internal_sender_description = odin.StringField()
    language = odin.StringField()
    payload_oxum = odin.StringField()
    record_creators = odin.ArrayField()
    source_organization = odin.StringField()
    title = odin.StringField()


class SourceCreator(odin.Resource):
    CREATOR_TYPE_CHOICES = (
        ("person", "Person"),
        ("organization", "Organization"),
        ("family", "Family")
    )
    name = odin.StringField()
    type = odin.StringField(choices=CREATOR_TYPE_CHOICES)


class SourceAgent(odin.Resource):
    AGENT_TYPE_CHOICES = (
        ("person", "Person"),
        ("organization", "Organization"),
        ("family", "Family")
    )
    type = odin.StringField(choices=AGENT_TYPE_CHOICES)
    name = odin.StringField()


class SourceAccession(odin.Resource):
    title = odin.StringField()
    url = odin.StringField()
    extent_size = odin.IntegerField()
    extent_files = odin.IntegerField()
    start_date = odin.DateField()
    end_date = odin.DateField()
    organization = odin.StringField()
    rights_statements = odin.ArrayOf(SourceRightsStatement)
    creators = odin.ArrayOf(SourceCreator)
    resource = odin.StringField()
    accession_date = odin.StringField()
    access_restrictions = odin.StringField()
    use_restrictions = odin.StringField()
    acquisition_type = odin.StringField()
    description = odin.StringField()
    appraisal_note = odin.StringField(null=True)
    accession_number = odin.ArrayField(null=True)


class SourceTransfer(odin.Resource):
    metadata = odin.DictAs(SourceMetadata)
    url = odin.StringField()
    rights_statements = odin.ArrayOf(SourceRightsStatement)
    resource = odin.StringField()
    archivesspace_parent_identifier = odin.StringField(null=True)


class SourcePackage(odin.Resource):
    fedora_uri = odin.StringField()
    use_statement = odin.StringField()
