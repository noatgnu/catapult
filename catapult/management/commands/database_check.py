import datetime
import subprocess
import time
import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.timezone import make_aware
from django.db import transaction
from catapult.models import Experiment, File, Analysis, CatapultRunConfig, ResultSummary
from catapult.tasks import run_analysis, run_quant, run_diann, run_diann_worker


def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


class Command(BaseCommand):
    """
    A command that will periodically check the database for file with size that has not changed in specified amount of time
    """

    def add_arguments(self, parser):
        parser.add_argument('--interval',
                            nargs="?",
                            type=int,
                            help='Interval to check the database in seconds',
                            default=10)
        parser.add_argument('--threshold',
                            nargs="?",
                            type=int,
                            help='Threshold to set file as ready',
                            default=5*60)
        parser.add_argument(
            "--queue",
            action="store_true",
            help="Process using queue",
        )


    def handle(self, interval: int, threshold: int, queue: bool, *args, **options):
        try:
            while True:

                files = File.objects.filter(
                    size__isnull=False,
                    ready_for_processing=False,
                    updated_at__lt=make_aware(datetime.datetime.now() - datetime.timedelta(seconds=threshold))
                )

                if files:
                    print(files)
                    file_d = files.filter(experiment__vendor=".d")
                    ready_files = files.filter(~Q(experiment__vendor=".d"))
                    for r in ready_files:
                        print(r.folder_watching_location.folder_path, r.file_path)
                        if r.size == os.path.getsize(r.get_path()):
                            r.ready_for_processing = True
                            r.save()
                    ready_files = list(ready_files)
                    with transaction.atomic():
                        for f in file_d:
                            folder_size = get_folder_size(f.get_path())
                            if folder_size == f.size:
                                f.ready_for_processing = True
                                ready_files.append(f)
                            else:
                                f.size = folder_size
                            f.save()

                configs = CatapultRunConfig.objects.filter(
                    analysis__isnull=False,
                    analysis__completed=False,
                    analysis__processing=False,
                )
                for config in configs:

                    if config.fasta_required:
                        for fasta in config.fasta.all():
                            if not fasta.ready:
                                fasta.check_ready()

                    if config.spectral_library_required:
                        for lib in config.spectral_library.all():
                            if not lib.ready:
                                lib.check_ready()
                    if config.check_fasta_ready() and config.check_spectral_library_ready():
                        analysis = config.analysis.first()
                        if analysis.total_files:
                            if analysis.generated_quant.all().count() == analysis.total_files:
                                commands = analysis.create_commands_from_config(dry_run=False, all_files=True)
                                analysis.processing = True
                                analysis.save()
                                if len(commands) > 0:
                                    if not queue:
                                        run_diann(commands=commands, analysis_id=analysis.id, config_id=config.id)
                                    else:
                                        run_diann_worker.enqueue(commands=commands, analysis_id=analysis.id,
                                                                 config_id=config.id)
                            else:
                                if analysis.generated_quant.all().count() < analysis.experiment.files.filter(
                                    ready_for_processing=True).count():
                                    commands = analysis.create_commands_from_config(dry_run=False)
                                    analysis.processing = True
                                    analysis.save()
                                    if len(commands) > 0:
                                        if not queue:
                                            run_diann(commands=commands, analysis_id=analysis.id, config_id=config.id)
                                        else:
                                            run_diann_worker.enqueue(commands=commands, analysis_id=analysis.id,
                                                                     config_id=config.id)
                        else:
                            if analysis.generated_quant.all().count() < analysis.experiment.files.filter(
                                    ready_for_processing=True).count():
                                commands = analysis.create_commands_from_config(dry_run=False)
                                analysis.processing = True
                                analysis.save()
                                if len(commands) > 0:
                                    if not queue:
                                        run_diann(commands=commands, analysis_id=analysis.id, config_id=config.id)
                                    else:
                                        run_diann_worker.enqueue(commands=commands, analysis_id=analysis.id, config_id=config.id)



                    # experiments = Experiment.objects.filter(
                    #                    files__in=ready_files,
                    #                    analysis__isnull=False,
                    #                    sample_count__isnull=False
                    # ).distinct()
                    #
                    # for e in experiments:
                    #     if e.ready_for_processing() and not e.is_being_processed() and not e.has_at_least_completed_analysis():
                    #         default_analysis = e.analysis.filter(default_analysis=True)
                    #         if default_analysis:
                    #             default_analysis = default_analysis.first()
                    #
                    #         default_analysis.processing = True
                    #         default_analysis.save()
                    #         run_analysis.delay(default_analysis.id)
                    #     elif not e.has_at_least_completed_analysis():
                    #         default_analysis = e.analysis.filter(default_analysis=True)
                    #         if default_analysis:
                    #             default_analysis = default_analysis.first()
                    #         ready_files = e.files.filter(ready_for_processing=True).count()
                    #         if default_analysis.generated_quant.all().count() < ready_files and default_analysis.generating_quant.all().count() < ready_files:
                    #             run_quant.delay(default_analysis.id)
                    #         else:
                    #             if e.ready_for_processing() and not e.is_being_processed():
                    #                 default_analysis.processing = True
                    #                 default_analysis.save()
                    #                 run_analysis.delay(default_analysis.id)

                print(f"Checking the database at {datetime.datetime.now()}")
                time.sleep(interval)
        except KeyboardInterrupt:
            quit(0)
