from rest_framework import serializers
from transformer.models import SourceObject, ConsumerObject


class SourceObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceObject
        fields = '__all__'


class ConsumerObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = ConsumerObject
        fields = '__all__'
