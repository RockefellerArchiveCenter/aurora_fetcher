import logging
from structlog import wrap_logger
from uuid import uuid4

from django_cron import CronJobBase, Schedule

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
        try:
            TransferRoutine().run()
        except Exception as e:
            self.log.error("Error processing transfers: ".format(e))
