from rest_framework import serializers

from .models import Package


class PackageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        fields = ('url', 'fedora_uri', 'bag_identifier', 'type',
                  'process_status', 'data', 'accession_data', 'created',
                  'last_modified')


class PackageListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        exclude = ('accession_data', 'data')
