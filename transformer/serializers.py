from rest_framework import serializers
from transformer.models import SourceObject, ConsumerObject, Identifier


class IdentifierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Identifier
        fields = '__all__'


class SourceObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceObject
        fields = '__all__'


class ConsumerObjectSerializer(serializers.ModelSerializer):
    identifiers = IdentifierSerializer(source='source_identifier', many=True)

    class Meta:
        model = ConsumerObject
        fields = '__all__'
