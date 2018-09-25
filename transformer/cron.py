import logging
from structlog import wrap_logger
from uuid import uuid4

from django_cron import CronJobBase, Schedule

from .clients import ArchivesSpaceClient
from .models import Transfer
from .routines import TransferRoutine


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger = wrap_logger(logger)


class ProcessTransfers(CronJobBase):
    RUN_EVERY_MINS = 0
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'transformer.process_transfers'

    def do(self):
        self.log = logger.new(transaction_id=str(uuid4()))
        routine = TransferRoutine(aspace_client=ArchivesSpaceClient())
        transfers = Transfer.objects.filter(process_status__lte=20)
        self.log.debug("Found {} transfers to process".format(len(transfers)))
        for transfer in transfers:
            self.log.debug("Running transfer routine", object=transfer)
            try:
                routine.run(transfer)
            except Exception as e:
                self.log.error("Error running transfer routine: {}".format(e), object=transfer)
                print(e)
