from datetime import datetime

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from .models import Package
from .routines import AccessionRoutine, GroupingComponentRoutine, TransferComponentRoutine, DigitalObjectRoutine, UpdateRequester
from .serializers import PackageSerializer, PackageListSerializer


def tuple_to_dict(data):
    detail = str(data[0])
    objects = data[1] if len(data) > 1 else []
    if objects and not isinstance(objects, list):
        objects = [objects]
    count = len(objects) if objects else 0
    return {"detail": detail, "objects": objects, "count": count}


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
        try:
            source_object = Package.objects.create(
                fedora_uri=request.data['uri'],
                identifier=request.data['identifier'],
                package_type=request.data['package_type'],
                process_status=Package.SAVED
            )
            serializer = PackageSerializer(source_object, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response("Error creating package: {}".format(str(e)))

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
            return Response(tuple_to_dict(response), status=200)
        except Exception as e:
            return Response(tuple_to_dict(e.args), status=500)


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


class UpdateRequestView(ProcessView):
    """Sends request with updated information to Aurora. Accepts POST requests only."""
    routine = UpdateRequester
