import os

from catapult_backend.celery import app

from django.core.management.base import BaseCommand, CommandError
from json import load
from catapult.models import CeleryWorker
import platform
import psutil
from datetime import datetime

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_system_info():
    uname = platform.uname()
    system_info = {
        "System": uname.system,
        "Node Name": uname.node,
        "Release": uname.release,
        "Version": uname.version,
        "Machine": uname.machine,
        "Processor": uname.processor,
        "Physical cores": psutil.cpu_count(logical=False),
        "Total cores": psutil.cpu_count(logical=True),
        "Total Memory": get_size(psutil.virtual_memory().total),
        "CPU Frequency": f"{psutil.cpu_freq().current:.2f}Mhz",
    }
    return system_info

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('config', type=str, help='Path to the worker config file')

    def handle(self, *args, **options):
        with open(options['config'], 'r') as f:
            config = load(f)

        worker = CeleryWorker.objects.get_or_create(worker_name=config["name"], worker_hostname=config["options"]["hostname"])[0]
        worker.worker_params = config
        worker.worker_info = get_system_info()
        worker.save()
        try:
            argv = [
                "-A",
                "catapult_backend",
                "worker",
                "-Q",
                config["options"]["Q"],
                f"--hostname={config['options']['hostname']}",
                "-P", config["options"]["P"],
                f"--loglevel={config['options']['loglevel']}", f"--logfile={config['options']['logfile']}"]
            if config["options"]["P"] != "solo":
                argv += [f"--concurrency={config['options']['concurrency']}"]
            os.environ["WORKER_HOSTNAME"] = config["options"]["hostname"]
            app.worker_main(argv=argv)
        except Exception as e:
            worker.worker_status = "Error"
            worker.worker_params = {"error": str(e)}
            worker.save()
            raise e
