import yaml

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
        parser.add_argument(
            "config",
            type=str,
            help="YAML configuration file",
        )
        parser.add_argument(
            "--experiment_id",
            nargs="?",
            default=0,
            type=int,
            help="Experiment ID (overrides config)",
        )
        parser.add_argument(
            "--output_folder",
            nargs="?",
            default="",
            type=str,
            help="Output folder (overrides config)",
        )

    def handle(self, config, experiment_id, output_folder, *args, **options):
        with open(config, "r") as f:
            config = yaml.safe_load(f)
            commands = [config["diann_path"]]
            experiment = None
            files = []
            print(config)
            if experiment_id and experiment_id > 0:
                experiment = Experiment.objects.get(id=experiment_id)
                files = File.objects.filter(experiment=experiment)
                if not output_folder:
                    output_folder = experiment.output_folder
                    os.makedirs(output_folder, exist_ok=True)

            for key, value in config.items():
                if key != "diann_path":
                    key = key.replace("_", "-")
                    if isinstance(value, bool) and value:
                        commands.append(f'--{key}')
                    elif isinstance(value, list):
                        if key == "unimod":
                            for item in value:
                                commands.append(f'--unimod{str(item)}')
                        elif key == "temp":
                            if len(output_folder) > 0:
                                commands.append(f'--temp')
                                commands.append(os.path.join(output_folder, "temp"))
                            else:
                                commands.append(f'--temp')
                                commands.append(str(value))
                        elif key == "f":
                            if len(files) > 0:
                                for f in files:
                                    commands.append(f'--f')
                                    commands.append(f.get_path())
                            else:
                                for item in value:
                                    commands.append(f'--{key}')
                                    commands.append(str(item))
                        elif key == "out":
                            if len(output_folder) > 0:
                                commands.append(f'--out')
                                commands.append(os.path.join(output_folder, "report.tsv"))
                            else:
                                commands.append(f'--out')
                                commands.append(str(value))

                        else:
                            for item in value:
                                commands.append(f'--{key}')
                                commands.append(str(item))
                    else:
                        commands.append(f'--{key}')
                        commands.append(str(value))
        print(commands)



