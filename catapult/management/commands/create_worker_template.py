import os
from json import dump

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    """
    A command that create a worker template
    """

    def add_arguments(self, parser):
        parser.add_argument('worker_name', type=str, help='Name of the worker')
        parser.add_argument('hostname', type=str, help='Hostname of the worker')

    def handle(self, *args, **options):
        worker_name = options['worker_name']
        worker_name = worker_name.replace(" ", "_")
        worker_name = worker_name.lower()
        celery_worker_template = {
            "name": worker_name,
            "type": "worker",
            "options": {
                "concurrency": 1,
                "loglevel": "INFO",
                "app": "catapult_backend",
                "hostname": f"{worker_name}@{options['hostname']}",
                "P": "solo",
                "Q": "default",
                "logfile": f"{worker_name}.log"
            },
            "folder_path_translations": {

            }
        }
        with open(f"{worker_name}.json", "w") as f:
            dump(celery_worker_template, f, indent=4)

