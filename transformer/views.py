from datetime import datetime
from django.views.generic import View

from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from client.clients import ArchivesSpaceClient
from transformer.models import SourceObject, ConsumerObject
from transformer.serializers import SourceObjectSerializer, ConsumerObjectSerializer
from transformer.transformers import ArchivesSpaceDataTransformer


class TransformViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def get_type(self, url):
        if 'transfers' in url:
            return 'component'
        if 'accession' in url:
            return 'accession'

    def create(self, request):
        type = self.get_type(request.data['url'])
        try:
            source_object = SourceObject.objects.create(
                source='aurora',
                type=type,
                data=request.data
            )
            transformer = ArchivesSpaceDataTransformer(
                data=request.data,
                type=type,
                source_object=source_object,
            )
            transformer.run()
            consumer_object = ConsumerObject.objects.get(source_object=source_object)
            serializer = ConsumerObjectSerializer(consumer_object, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


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
