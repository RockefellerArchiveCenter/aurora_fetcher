import logging
from structlog import wrap_logger
from uuid import uuid4

from django_cron import CronJobBase, Schedule

from clients.clients import ArchivesSpaceClient, AuroraClient
from transformer.models import SourceObject, ConsumerObject
from transformer.routines import AccessionRoutine
from transformer.transformers import ArchivesSpaceDataTransformer


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
                self.log.error("Error running accession routine: {}".format(e), object=accession)
                print(e)


class RetrieveFailed(CronJobBase):
    RUN_EVERY_MINS = 0
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'transformer.retrieve_failed'

    def do(self):
            self.log = logger.new(transaction_id=str(uuid4()))
            self.aurora_client = AuroraClient()
            self.aspace_client = ArchivesSpaceClient()
            self.transformer = ArchivesSpaceDataTransformer(aspace_client=self.aspace_client)
            for accession in self.aurora_client.retrieve_paged('accessions/', params={"process_status": 10}):
                try:
                    data = self.aurora_client.retrieve(accession['url'])
                    consumer_data = self.transformer.transform_accession(data)
                    aspace_identifier = self.aspace_client.create(consumer_data, 'accession')
                    if aspace_identifier:
                        consumer_object = ConsumerObject().initial_save(consumer_data=consumer_data, identifier=aspace_identifier, type='accession', source_data=data)
                        data['process_status'] = 20
                        self.aurora_client.update(data['url'], data)
                except Exception as e:
                    self.log.error("Error getting accessions: {}".format(e), object=accession['url'])
                    print(e)
