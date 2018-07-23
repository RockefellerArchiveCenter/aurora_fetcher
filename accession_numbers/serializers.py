from rest_framework import serializers
from accession_numbers.models import AccessionNumber


class AccessionNumberSerializer(serializers.HyperlinkedModelSerializer):
    display_string = serializers.StringRelatedField(source='__str__')

    class Meta:
        model = AccessionNumber
        fields = (
            'url', 'display_string', 'segment_1', 'segment_2', 'segment_3',
            'segment_4', 'created_time', 'last_modified_time')


class NextAccessionNumberSerializer(serializers.HyperlinkedModelSerializer):
    display_string = serializers.StringRelatedField(source='__str__')

    class Meta:
        model = AccessionNumber
        fields = (
            'display_string', 'segment_1', 'segment_2', 'segment_3',
            'segment_4')
