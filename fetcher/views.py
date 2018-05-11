from datetime import datetime

from django.shortcuts import render
from django.views.generic import View
from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from fetcher.models import SourceObject
from fetcher.serializers import SourceObjectSerializer


class HomeView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'fetcher/main.html')


class FetcherViewSet(viewsets.ModelViewSet):
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
            type=type,
            data=request.data  # check if this is accurate
        )
        serializer = SourceObjectSerializer(source_object, context={'request': request})
        return Response(serializer.data)

    def update(self, request, pk=None):
        source_object = Component.objects.update(
            pk=pk,
            type=type,
            data=request.data  # check if this is accurate
        )
        serializer = SourceObjectSerializer(source_object, context={'request': request})
        return Response(serializer.data)
