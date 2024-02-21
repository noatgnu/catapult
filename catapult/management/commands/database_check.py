import datetime
import time
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import make_aware

from catapult.models import Experiment, File, Analysis
from catapult.tasks import run_analysis, run_quant


class Command(BaseCommand):
    """
    A command that will periodically check the database for file with size that has not changed in specified amount of time
    """

    def add_arguments(self, parser):
        parser.add_argument('interval', type=int, help='Interval to check the database in seconds', default=10)
        parser.add_argument('threshold', type=int, help='Threshold to set file as ready', default=5*60)


    def handle(self, *args, **options):
        interval = options['interval']
        try:
            while True:
                files = File.objects.filter(size__isnull=False, ready_for_processing=False, updated_at__lt=make_aware(datetime.datetime.now() - datetime.timedelta(seconds=options['threshold'])))
                if files:
                    files.update(ready_for_processing=True)
                    experiments = Experiment.objects.filter(
                                       files__in=files,
                                       analysis__isnull=False,
                                       sample_count__isnull=False
                    ).distinct()
                    for e in experiments:
                        if e.ready_for_processing() and not e.is_being_processed() and not e.has_at_least_completed_analysis():
                            default_analysis = e.analysis.filter(default_analysis=True)
                            if default_analysis:
                                default_analysis = default_analysis.first()

                            default_analysis.processing = True
                            default_analysis.save()
                            run_analysis.delay(default_analysis.id)
                        elif not e.has_at_least_completed_analysis():
                            default_analysis = e.analysis.filter(default_analysis=True)
                            if default_analysis:
                                default_analysis = default_analysis.first()
                            ready_files = e.files.filter(ready_for_processing=True).count()
                            if default_analysis.generated_quant.all().count() < ready_files and default_analysis.generating_quant.all().count() < ready_files:
                                run_quant.delay(default_analysis.id)
                            else:
                                if e.ready_for_processing() and not e.is_being_processed():
                                    default_analysis.processing = True
                                    default_analysis.save()
                                    run_analysis.delay(default_analysis.id)

                print(f"Checking the database at {datetime.datetime.now()}")
                time.sleep(interval)
        except KeyboardInterrupt:
            quit(0)