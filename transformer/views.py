from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from rest_framework import viewsets
from rest_framework.response import Response

from transformer.models import Transfer, Identifier
from transformer.serializers import TransferSerializer, TransferListSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferViewSet(viewsets.ModelViewSet):
    """
    Endpoint for Transfers.

    create:
    Creates a Transfer.

    list:
    Returns a list of Transfers. Accepts query parameter `updated_since`.

    retrieve:
    Returns a single Transfer, identified by a primary key.
    """
    model = Transfer
    serializer_class = TransferSerializer

    def create(self, request):
        self.log.bind(request_id=str(uuid4()))
        source_object = Transfer.objects.create(
            fedora_uri=request.data['uri'],
            internal_sender_identifier=request.data['identifier'],
            package_type=request.data['package_type']
        )
        serializer = TransferSerializer(source_object, context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        queryset = Transfer.objects.all()
        updated_since = self.request.GET.get('updated_since', "")
        if updated_since != "":
            queryset = queryset.filter(last_modified__gte=datetime.fromtimestamp(int(updated_since)))
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return TransferListSerializer
        return TransferSerializer
