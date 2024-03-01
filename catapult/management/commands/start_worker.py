from catapult_backend.celery import app

from django.core.management.base import BaseCommand, CommandError
from json import load
from catapult.models import CeleryWorker


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('config', type=str, help='Path to the worker config file')

    def handle(self, *args, **options):
        with open(options['config'], 'r') as f:
            config = load(f)

        worker = CeleryWorker.objects.get_or_create(worker_name=config["name"], worker_hostname=config["options"]["hostname"])[0]
        worker.worker_status = "Running"
        worker.worker_params = config
        worker.save()

        app.worker_main(argv=[
            "-A",
            "catapult_backend",
            "worker",
            "-Q",
            config["options"]["Q"],
            f"--hostname={config['options']['hostname']}",
            "-P", config["options"]["P"],
            f"--loglevel={config['options']['loglevel']}", f"--logfile={config['options']['logfile']}"])
