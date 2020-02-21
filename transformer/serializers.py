from rest_framework import serializers

from .models import Package


class PackageSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        fields = ('url', 'fedora_uri', 'identifier', 'package_type', 'process_status', 'transfer_data', 'accession_data', 'created', 'last_modified')


class PackageListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Package
        exclude = ('accession_data', 'transfer_data')
