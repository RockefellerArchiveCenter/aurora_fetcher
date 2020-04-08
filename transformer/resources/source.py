import odin


class SourceRightsStatement(odin.Resource):
    pass


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
