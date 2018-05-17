from datetime import datetime
from django.views.generic import View

from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from client.clients import ArchivesSpaceClient
from transformer.models import SourceObject, ConsumerObject, Identifier
from transformer.serializers import SourceObjectSerializer, ConsumerObjectSerializer
from transformer.transformers import ArchivesSpaceDataTransformer


class TransformViewSet(viewsets.ViewSet):
    """Accepts Accession records from Aurora, transforms and saves data to ArchivesSpace"""
    permission_classes = (IsAuthenticated,)
    transformer = ArchivesSpaceDataTransformer
    client = ArchivesSpaceClient

    def create(self, request):
        if 'accession' not in request.data['url']:
            Response("Incorrect object type", status=status.HTTP_400_BAD_REQUEST)
        consumer_data = self.transformer().transform_accession(request.data)
        as_identifier = self.client().save_data(consumer_data, 'accession')
        if not consumer_data:
            return Response("Error transforming data.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not as_identifier:
            return Response("Error saving data in ArchivesSpace.", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        source_object = SourceObject.objects.create(
            source='aurora',
            type='accession',
            data=request.data,
            process_status=10
        )
        consumer_object = ConsumerObject.objects.create(
            consumer='archivesspace',
            type='accession',
            source_object=source_object,
            data=consumer_data,
        )
        identifier = Identifier.objects.create(
            source='archivesspace',
            identifier=as_identifier,
            consumer_object=consumer_object,
        )
        serializer = ConsumerObjectSerializer(consumer_object, context={'request': request})
        return Response(serializer.data)



class SourceObjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    model = SourceObject
    serializer_class = SourceObjectSerializer

    def get_queryset(self):
        queryset = SourceObject.objects.all()
        updated_since = self.request.GET.get('updated_since', "")
        type = self.request.GET.get('type', "")
        if updated_since != "":
            queryset = queryset.filter(last_modified__gte=datetime.fromtimestamp(int(updated_since)))
        if type != "":
            queryset = queryset.filter(type=type)
        return queryset


class ConsumerObjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    model = ConsumerObject
    serializer_class = ConsumerObjectSerializer

    def get_queryset(self):
        queryset = ConsumerObject.objects.all()
        updated_since = self.request.GET.get('updated_since', "")
        type = self.request.GET.get('type', "")
        if updated_since != "":
            queryset = queryset.filter(last_modified__gte=datetime.fromtimestamp(int(updated_since)))
        if type != "":
            queryset = queryset.filter(type=type)
        return queryset
