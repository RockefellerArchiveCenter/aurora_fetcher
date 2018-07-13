from datetime import date
import logging
import re
from structlog import wrap_logger
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.views.generic import View
from accession_numbers.cron import ArchivesSpaceAccessionNumbers
from accession_numbers.models import AccessionNumber
from accession_numbers.serializers import AccessionNumberSerializer, NextAccessionNumberSerializer
from rest_framework import viewsets, generics, status
from rest_framework.response import Response

logger = wrap_logger(logger=logging.getLogger(__name__))


class HomeView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'accession_numbers/main.html')


class AccessionNumberViewSet(viewsets.ModelViewSet):
    """
list:
Returns a list of accession numbers, ordered by most recent. Accepts `year` \
as a query parameter, which limits results to the years specified.

retrieve:
Returns a single accession number, identified by a primary key.

create:
Creates an accession number.

update:
Updates an existing accession number, identified by a primary key.

destroy:
Deletes an existing accession number, identified by a primary key.
    """
    model = AccessionNumber
    serializer_class = AccessionNumberSerializer
    queryset = AccessionNumber.objects.all()

    def list(self, request):
        year = self.request.GET.get('year', None)
        if year:
            numbers = AccessionNumber.objects.filter(segment_1=year).order_by('-segment_1', '-segment_2', '-segment_3', '-segment_4')
        else:
            numbers = AccessionNumber.objects.all().order_by('-segment_1', '-segment_2', '-segment_3', '-segment_4')
        page = self.paginate_queryset(numbers)
        if page is not None:
            serializer = AccessionNumberSerializer(page, context={'request': request}, many=True)
            return self.get_paginated_response(serializer.data)
        return Response()

    def create(self, request):
        log = logger.bind(request_id=str(uuid4()))
        accession_number = AccessionNumber(
            segment_1=request.data['segment_1'],
            segment_2=request.data['segment_2'],
            segment_3=request.data['segment_3'],
            segment_4=request.data['segment_4'],
            in_archivesspace=False,
        )
        try:
            accession_number.full_clean()
            if AccessionNumber.objects.filter(
                segment_1=request.data['segment_1'],
                segment_2=request.data['segment_2'],
                segment_3=request.data['segment_3'],
                segment_4=request.data['segment_4'],
            ).exists():
                log.debug("Accession number already exists, ignoring")
                return Response("Accession number already exists.", status=400)
            else:
                accession_number.save()
                log.debug("Accession number created", object=accession_number)
                accession_number_serializer = AccessionNumberSerializer(accession_number, context={'request': request})
                return Response(accession_number_serializer.data)

        except ValidationError as e:
            log.error(e)
            return Response(e, status=400)


class NextAccessionNumberView(generics.RetrieveAPIView):
    """
retrieve:
Returns the next accession number. If the query parameter `year` is supplied, \
returns the next accession number in that year. If not, returns the next \
number in the current year.
    """
    model = AccessionNumber
    serializer_class = NextAccessionNumberSerializer

    def get_object(self):
        log = logger.bind(request_id=str(uuid4()))
        # Not sure if this is a good idea. Has the potential to really slow down the response.
        ArchivesSpaceAccessionNumbers().do()
        year = self.request.GET.get('year', date.today().year)
        if AccessionNumber.objects.filter(segment_1=year).exists():
            last_accession = AccessionNumber.objects.filter(segment_1=year).order_by('-segment_2')[0]
            try:
                next_number = int(re.sub('[^0-9]', '', last_accession.segment_2))
                next_number += 1
            except Exception as e:
                log.error(e)
                return False
        else:
            next_number = 1
        next_accession_number = AccessionNumber(
            segment_1=year,
            segment_2=str(next_number).zfill(3),
            in_archivesspace=False,
        )
        log.debug("Next accession number returned", object=next_accession_number)
        return next_accession_number
