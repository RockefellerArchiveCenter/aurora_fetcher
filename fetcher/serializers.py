from rest_framework import serializers
from fetcher.models import SourceObject


class SourceObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceObject
        fields = '__all__'
