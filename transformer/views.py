from datetime import datetime

from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from client.clients import ArchivesSpaceClient
from transformer.models import SourceObject, ConsumerObject
from transformer.serializers import SourceObjectSerializer, ConsumerObjectSerializer
from transformer.transformers import DataTransformer


class SourceObjectViewSet(viewsets.ModelViewSet):
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

    def get_type(self, url):
        if 'transfers' in url:
            return 'component'
        if 'accession' in url:
            return 'accession'

    def create(self, request):
        type = self.get_type(request.data['url'])
        source_object = SourceObject.objects.create(
            source='aurora',
            type=type,
            data=request.data
        )
        try:
            archivesspace_data = DataTransformer().to_archivesspace(request.data)
            consumer_object = ConsumerObject.objects.create(
                consumer='archivesspace',
                type=type,
                source_object=source_object,
                data=archivesspace_data,
            )
            deliver = ArchivesSpaceClient().post(archivesspace_data)
            serializer = SourceObjectSerializer(source_object, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(e, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        type = self.get_type(request.data['url'])
        source_object = Component.objects.update(
            pk=pk,
            type=type,
            data=request.data
        )
        serializer = SourceObjectSerializer(source_object, context={'request': request})
        return Response(serializer.data)


class ConsumerObjectViewSet(viewsets.ModelViewSet):
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
