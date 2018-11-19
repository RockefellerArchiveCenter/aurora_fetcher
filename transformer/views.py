from datetime import datetime
import logging
from structlog import wrap_logger
import urllib
from uuid import uuid4

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from .models import Package
from .routines import AccessionRoutine, GroupingComponentRoutine, TransferComponentRoutine, DigitalObjectRoutine
from .serializers import PackageSerializer, PackageListSerializer

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class PackageViewSet(ModelViewSet):
    """
    Endpoint for packages.

    create:
    Creates a Package.

    list:
    Returns a list of Packages. Accepts query parameter `updated_since`.

    retrieve:
    Returns a single Package, identified by a primary key.
    """
    model = Package
    serializer_class = PackageSerializer

    def create(self, request):
        source_object = Package.objects.create(
            fedora_uri=request.data['uri'],
            identifier=request.data['identifier'],
            package_type=request.data['package_type'],
            process_status=Package.SAVED
        )
        serializer = PackageSerializer(source_object, context={'request': request})
        return Response(serializer.data)

    def get_queryset(self):
        queryset = Package.objects.all()
        updated_since = self.request.GET.get('updated_since', "")
        if updated_since != "":
            queryset = queryset.filter(last_modified__gte=datetime.fromtimestamp(int(updated_since)))
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return PackageListSerializer
        return PackageSerializer


class ProcessView(APIView):
    def post(self, request, format=None):
        log = logger.new(transaction_id=str(uuid4()))

        try:
            message = self.routine().run()
            return Response({"detail": message}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)


class ProcessAccessionsView(ProcessView):
    """Runs the AccessionRoutine. Accepts POST requests only."""
    def __init__(self):
        self.routine = AccessionRoutine


class ProcessGroupingComponentsView(ProcessView):
    """Runs the GroupingComponentRoutine. Accepts POST requests only."""
    def __init__(self):
        self.routine = GroupingComponentRoutine


class ProcessTransferComponentsView(ProcessView):
    """Runs the TransferComponentRoutine. Accepts POST requests only."""
    def __init__(self):
        self.routine = TransferComponentRoutine


class ProcessDigitalObjectsView(ProcessView):
    """Runs the DigitalObjectRoutine. Accepts POST requests only."""
    def __init__(self):
        self.routine = DigitalObjectRoutine


class UpdateRequestView(APIView):
    """Sends request with updated information to Aurora. Accepts POST requests only."""

    def post(self, request):
        log = logger.new(transaction_id=str(uuid4()))
        url = request.GET.get('post_service_url')
        url = (urllib.parse.unquote(url) if url else '')
        try:
            update = UpdateRequester(url).run()
            return Response({"detail": update}, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=500)
