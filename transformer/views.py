from datetime import datetime
import logging
from structlog import wrap_logger
from uuid import uuid4

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from .models import Transfer
from .routines import TransferRoutine
from .serializers import TransferSerializer, TransferListSerializer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class TransferViewSet(ModelViewSet):
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
        source_object = Transfer.objects.create(
            fedora_uri=request.data['uri'],
            identifier=request.data['identifier'],
            package_type=request.data['package_type'],
            process_status=10
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


class ProcessTransfersView(APIView):
    """Runs the ProcessTransfers routine. Accepts POST requests only."""

    def post(self, request, format=None):
        log = logger.new(transaction_id=str(uuid4()))
        try:
            transfers = TransferRoutine().run()
            return Response({"detail": transfers}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
