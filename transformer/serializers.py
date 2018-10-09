from rest_framework import serializers
from .models import Transfer


class TransferSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Transfer
        fields = ('url', 'fedora_uri', 'identifier', 'package_type', 'process_status', 'transfer_data', 'accession_data', 'created', 'last_modified')


class TransferListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Transfer
        exclude = ('accession_data', 'transfer_data')
