from catapult.models import File, FolderWatchingLocation, Experiment, Analysis
from django.core.management.base import BaseCommand, CommandError

import os
import datetime
import subprocess

class Command(BaseCommand):
    """
    A command that runs experiments
    """

    def add_arguments(self, parser):
        parser.add_argument('experiment_id', type=int, help='Experiment ID')
        parser.add_argument('output_folder', type=str, help='Output folder')
        parser.add_argument('diann_path', type=str, help='Path to the diann executable')

    def handle(self, *args, **options):
        experiment_id = options['experiment_id']
        output_folder = options['output_folder']
        diann_path = options['diann_path']
        experiment = Experiment.objects.get(id=experiment_id)
        files = File.objects.filter(experiment=experiment)
        experiment.output_folder = output_folder
        experiment.save()
        os.makedirs(output_folder, exist_ok=True)
        temp_folder = os.path.join(output_folder, "temp")
        os.makedirs(temp_folder, exist_ok=True)
        commands = [diann_path]
        for f in files:
            commands.append("--f")
            commands.append(f.file_path)
        cpu_count = os.cpu_count()
        commands.extend(
            [
                "--lib",
                "--threads",
                str(cpu_count),
                "--verbose",
                "4",
                "--out",
                os.path.join(output_folder, "report.tsv"),
                "--qvalue", "0.01", "--matrices", "--temp", temp_folder,
                "--out-lib",
                os.path.join(output_folder, "report-lib.tsv"),
                "--gen-spec-lib",
                "--predictor",
                "--fasta", experiment.fasta_file,
                "--fasta-search",
                "--min-fr-mz", "200",
                "--max-fr-mz", "1800",
                "--cut", "K*,R*",
                "--missed-cleavages", "2",
                "--min-pep-len", "7",
                "--max-pep-len", "30",
                "--min-pr-mz", "300",
                "--max-pr-mz", "1800",
                "--min-pr-charge", "1",
                "--max-pr-charge", "4",
                "--unimod4",
                "--var-mods", "1",
                "--var-mod", "UniMod:35,15.994915,M",
                "--mass-acc", "20",
                "--mass-acc-ms1", "20",
                "--individual-mass-acc",
                "--individual-windows",
                "--reanalyse",
                "--smart-profiling",
                "--peak-center", "--no-ifs-removal"
            ]
        )
        analysis = Analysis.objects.create(experiment=experiment, start_time=datetime.datetime.now(), analysis_name="Test DIA-NN Thermo Raw search", analysis_type="DIA-NN Library-based Search", commands=" ".join(commands))
        start_time = datetime.datetime.now()
        analysis.start_time = start_time
        analysis.processing = True
        subprocess.run(analysis.commands, shell=True, check=True)
        end_time = datetime.datetime.now()
        analysis.end_time = end_time
        analysis.processing = False
        analysis.completed = True
        analysis.save()



