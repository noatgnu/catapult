import yaml
from django.core.management import BaseCommand

from catapult.util import extract_cmd_from_diann_log, convert_cmd_to_array, convert_cmd_array_to_config

class Command(BaseCommand):
    help = "Create a DIANN config from a log file"

    def add_arguments(self, parser):
        parser.add_argument("log_path", type=str, help="Path to the log file")
        parser.add_argument("--output", type=str, help="Path to the output file", default="config.yaml")

    def handle(self, log_path, output, *args, **options):
        cmd = extract_cmd_from_diann_log(log_path)
        cmd_array = convert_cmd_to_array(cmd)
        config = convert_cmd_array_to_config(cmd_array)
        with open(output, "w") as f:
            yaml.dump(config, f)