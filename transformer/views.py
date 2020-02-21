from datetime import datetime

from asterism.views import prepare_response
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Package
from .routines import (AccessionRoutine, AccessionUpdateRequester,
                       DigitalObjectRoutine, GroupingComponentRoutine,
                       TransferComponentRoutine, TransferUpdateRequester)
from .serializers import PackageListSerializer, PackageSerializer


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
        """Create a package object and based on data supplied with a request. If request
        data contains `archivesspace_uri`, add that URI to `transfer_data` and set
        `process_status` to TRANSFER_COMPONENT_CREATED."""
        try:
            source_object = Package.objects.create(
                fedora_uri=request.data.get('uri'),
                identifier=request.data.get('identifier'),
                package_type=request.data.get('package_type'),
                process_status=Package.SAVED
            )
            if request.data.get('origin') in ['digitization', 'legacy_digital']:
                # TODO: investigate using defaultdict for this
                source_object.transfer_data = {
                    'data': {
                        'archivesspace_identifier': request.data['archivesspace_uri']
                    }
                }
                source_object.process_status = Package.TRANSFER_COMPONENT_CREATED
                source_object.origin = request.data.get('origin')
                source_object.save()
            return Response(prepare_response(("Package created", source_object.identifier)))
        except Exception as e:
            return Response(prepare_response("Error creating package: {}".format(str(e))), status=500)

    def get_queryset(self):
        queryset = Package.objects.all().order_by('-last_modified')
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
        try:
            response = self.routine().run()
            return Response(prepare_response(response), status=200)
        except Exception as e:
            return Response(prepare_response(e), status=500)


class ProcessAccessionsView(ProcessView):
    """Runs the AccessionRoutine. Accepts POST requests only."""
    routine = AccessionRoutine


class ProcessGroupingComponentsView(ProcessView):
    """Runs the GroupingComponentRoutine. Accepts POST requests only."""
    routine = GroupingComponentRoutine


class ProcessTransferComponentsView(ProcessView):
    """Runs the TransferComponentRoutine. Accepts POST requests only."""
    routine = TransferComponentRoutine


class ProcessDigitalObjectsView(ProcessView):
    """Runs the DigitalObjectRoutine. Accepts POST requests only."""
    routine = DigitalObjectRoutine


class TransferUpdateRequestView(ProcessView):
    """Sends request with updated information to Aurora. Accepts POST requests only."""
    routine = TransferUpdateRequester


class AccessionUpdateRequestView(ProcessView):
    """Sends request with updated information to Aurora. Accepts POST requests only."""
    routine = AccessionUpdateRequester
