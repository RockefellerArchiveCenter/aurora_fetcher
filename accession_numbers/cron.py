import json
import logging
from os.path import isfile, join
import pickle
from structlog import wrap_logger
import time
from uuid import uuid4

from django_cron import CronJobBase, Schedule
from django.core.exceptions import ValidationError

from aquarius import settings
from accession_numbers.models import AccessionNumber
from transformer.clients import ArchivesSpaceClient, ArchivesSpaceClientError

logger = wrap_logger(logger=logging.getLogger(__name__))


def read_time(time_filepath, log):
    if isfile(time_filepath):
        with open(time_filepath, 'rb') as pickle_handle:
            last_export = str(pickle.load(pickle_handle))
    else:
        last_export = 0
    log.debug("Got last update time of {time}".format(time=last_export))
    return last_export


def update_time(export_time, time_filepath, log):
    with open(time_filepath, 'wb') as pickle_handle:
        pickle.dump(export_time, pickle_handle)
    log.debug("Last update time set to {time}".format(time=export_time))


class ArchivesSpaceAccessionNumbers(CronJobBase):
    RUN_EVERY_MINS = 0
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'accession_numbers.archivesspace_accession_numbers'

    def do(self, last_crawl_time=None):
        log = logger.new(transaction_id=str(uuid4()))
        try:
            log.info("Started polling ArchivesSpace for accession_numbers")
            new_update_time = int(time.time())
            last_crawl_time = last_crawl_time if last_crawl_time else read_time(join(settings.BASE_DIR, 'as_update_time.pickle'), log)
            client = ArchivesSpaceClient()
            accessions = client.retrieve('repositories/{repo_id}/accessions'.format(repo_id=settings.ARCHIVESSPACE['repo_id']), params={'all_ids': True, 'last_modified': last_crawl_time})
            for acc_id in accessions:
                log.bind(request_id=str(uuid4()))
                acc = client.retrieve('repositories/{repo_id}/accessions/{acc_id}'.format(repo_id=settings.ARCHIVESSPACE['repo_id'], acc_id=str(acc_id)))
                accession_number = AccessionNumber(
                    segment_1=acc.get('id_0', None),
                    segment_2=acc.get('id_1', None),
                    segment_3=acc.get('id_2', None),
                    segment_4=acc.get('id_3', None),
                    in_archivesspace=True,
                )
                log.bind(object=accession_number)
                try:
                    accession_number.full_clean()
                    if not AccessionNumber.objects.filter(
                        segment_1=acc.get('id_0', None),
                        segment_2=acc.get('id_1', None),
                        segment_3=acc.get('id_2', None),
                        segment_4=acc.get('id_3', None),
                    ).exists():
                        accession_number.save()
                        log.debug("Created accession number")
                    else:
                        log.debug("Accession number already exists")
                except ValidationError as e:
                    log.error(e)
            update_time(new_update_time, join(settings.BASE_DIR, 'as_update_time.pickle'), log)
            log.info("Finished polling ArchivesSpace for new or changed accessions")
        except ArchivesSpaceClientError:
            log.error(e, request_id=str(uuid4()))
