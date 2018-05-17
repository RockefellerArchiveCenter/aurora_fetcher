from rest_framework import serializers
from transformer.models import SourceObject, ConsumerObject, Identifier


class IdentifierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Identifier
        exclude = ('id',)


class SourceObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceObject
        fields = ('id', 'type', 'source', 'data', 'created', 'last_modified')


class ConsumerObjectSerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(source='source_identifier', many=True)

    class Meta:
        model = ConsumerObject
        fields = ('id', 'type', 'source_object', 'consumer', 'identifiers', 'data', 'created', 'last_modified')
