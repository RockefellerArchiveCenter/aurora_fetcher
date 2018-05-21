from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from django.shortcuts import render
from django.views.generic import View

from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from client.clients import ArchivesSpaceClient
from transformer.models import SourceObject, ConsumerObject, Identifier
from transformer.serializers import SourceObjectSerializer, SourceObjectListSerializer, ConsumerObjectSerializer, ConsumerObjectListSerializer
from transformer.transformers import ArchivesSpaceDataTransformer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class HomeView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'transformer/main.html')


class TransformViewSet(viewsets.ViewSet):
    """Accepts Accession records from Aurora, transforms and saves data to ArchivesSpace"""
    permission_classes = (IsAuthenticated,)
    log = logger

    def create(self, request):
        self.log.bind(request_id=str(uuid4()))
        self.client = ArchivesSpaceClient()
        self.transformer = ArchivesSpaceDataTransformer(aspace_client=self.client)
        if 'accession' not in request.data['url']:
            self.log.error("Incorrect object type, must be an accession", object=request.data['url'])
            return Response({"detail": "Incorrect object type, must be an accession"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            consumer_data = self.transformer.transform_accession(request.data)
            aspace_identifier = self.client.create(consumer_data, 'accession')
        except Exception as e:
            return Response({"detail": "{}".format(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        consumer_object = ConsumerObject().initial_save(consumer_data=consumer_data, identifier=aspace_identifier, type='accession', source_data=request.data)
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

    def get_serializer_class(self):
        if self.action == 'list':
            return SourceObjectListSerializer
        return SourceObjectSerializer


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

    def get_serializer_class(self):
        if self.action == 'list':
            return ConsumerObjectListSerializer
        return ConsumerObjectSerializer
