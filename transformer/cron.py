import logging
from structlog import wrap_logger
from uuid import uuid4

from django_cron import CronJobBase, Schedule

from client.clients import ArchivesSpaceClient, AuroraClient
from transformer.models import SourceObject
from transformer.routines import AccessionRoutine


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class ProcessAccessions(CronJobBase):
    RUN_EVERY_MINS = 0
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'transformer.process_accessions'

    def do(self):
        self.log = logger.new(transaction_id=str(uuid4()))
        routine = AccessionRoutine(
            aspace_client=ArchivesSpaceClient(),
            aurora_client=AuroraClient()
        )
        accessions = SourceObject.objects.filter(type='accession', process_status__lte=30)
        self.log.debug("Found {} accessions to process".format(len(accessions)))
        for accession in accessions:
            self.log.debug("Running accession routine", object=accession)
            try:
                routine.run(accession)
            except Exception as e:
                print(e)
