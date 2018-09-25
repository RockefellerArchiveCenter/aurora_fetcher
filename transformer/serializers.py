from rest_framework import serializers
from .models import Transfer, Identifier


class IdentifierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Identifier
        exclude = ('id', 'consumer_object')


class TransferSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Transfer
        fields = ('url', 'fedora_uri', 'internal_sender_identifier', 'package_type', 'transfer_data', 'accession_data', 'created', 'last_modified')


class TransferListSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Transfer
        exclude = ('accession_data', 'transfer_data')
