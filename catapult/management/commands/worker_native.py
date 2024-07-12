import json
import logging
import platform
import random
import time
from argparse import ArgumentParser
from types import FrameType
from typing import Optional

import psutil
from django.core.management import BaseCommand
from django.db import transaction
from django_tasks import DEFAULT_QUEUE_NAME, DEFAULT_TASK_BACKEND_ALIAS
from django_tasks.backends.database.management.commands.db_worker import valid_interval, valid_backend_name, logger, \
    Worker
from django_tasks.backends.database.models import DBTaskResult

from catapult.models import CeleryWorker, CeleryTask

logger = logging.getLogger("catapult.worker")


class CatapultWorker(Worker):
    def __init__(self, *args, **kwargs):
        self.c_worker: CeleryWorker = kwargs["c_worker"]
        kwargs.pop("c_worker")
        super().__init__(*args, **kwargs)


    def start(self) -> None:
        self.configure_signals()

        logger.info("Starting worker for queues=%s", ",".join(self.queue_names))

        if self.interval:
            # Add a random small delay before starting the loop to avoid a thundering herd
            time.sleep(random.random())

        while self.running:
            tasks = DBTaskResult.objects.ready().filter(backend_name=self.backend_name)
            if not self.process_all_queues:
                tasks = tasks.filter(queue_name__in=self.queue_names)

            try:
                self.running_task = True

                # During this transaction, all "ready" tasks are locked. Therefore, it's important
                # it be as efficient as possible.
                with transaction.atomic():
                    task_result = tasks.get_locked()

                    if task_result is not None:
                        # "claim" the task, so it isn't run by another worker process
                        if "task_id" in task_result.args_kwargs["kwargs"]:
                            ui = task_result.args_kwargs["kwargs"]["task_id"]
                            c_task = CeleryTask.objects.get_or_create(task_id=ui)[0]
                            c_task.task_id = str(task_result.id)
                        else:
                            c_task = CeleryTask.objects.get_or_create(task_id=str(task_result.id))[0]
                            c_task.status = "PENDING"
                            task_result.args_kwargs["kwargs"]["task_id"] = c_task.task_id
                        task_result.args_kwargs["kwargs"]["worker_hostname"] = self.c_worker.worker_hostname
                        task_result.save(update_fields=["args_kwargs"])
                        c_task.save()
                        self.c_worker.tasks.add(c_task)

                        task_result.claim()

                if task_result is not None:
                    self.run_task(task_result)

            finally:
                self.running_task = False

            if self.batch and task_result is None:
                # If we're running in "batch" mode, terminate the loop (and thus the worker)
                return None

            # Wait before checking for another task
            time.sleep(self.interval)

    def shutdown(self, signum: int, frame: Optional[FrameType]) -> None:
        self.c_worker.worker_info = get_system_info()
        self.c_worker.worker_status = "OFFLINE"
        self.c_worker.save()

        super().shutdown(signum, frame)


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
    help = "Run a database background worker"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--queue-name",
            nargs="?",
            default=DEFAULT_QUEUE_NAME,
            type=str,
            help="The queues to process. Separate multiple with a comma. To process all queues, use '*' (default: %(default)r)",
        )
        parser.add_argument(
            "--interval",
            nargs="?",
            default=1,
            type=valid_interval,
            help="The interval (in seconds) at which to check for tasks to process (default: %(default)r)",
        )
        parser.add_argument(
            "--batch",
            action="store_true",
            help="Process all outstanding tasks, then exit",
        )
        parser.add_argument(
            "--backend",
            nargs="?",
            default=DEFAULT_TASK_BACKEND_ALIAS,
            type=valid_backend_name,
            dest="backend_name",
            help="The backend to operate on (default: %(default)r)",
        )
        parser.add_argument(
            "--config",
            type=str,
            help="Path to the worker config file",
        )

    def configure_logging(self, verbosity: int, logging_path: str) -> None:
        logger = logging.getLogger(f"catapult.worker{logging_path}")
        if verbosity == 0:
            logger.setLevel(logging.CRITICAL)
        elif verbosity == 1:
            logger.setLevel(logging.WARNING)
        elif verbosity == 2:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        # If no handler is configured, the logs won't show,
        # regardless of the set level.
        if not logger.hasHandlers():
            # Use FileHandler instead of StreamHandler
            handler = logging.FileHandler(logging_path)

            # Set the format for the handler
            formatter = logging.Formatter('[%(asctime)s: %(levelname)s]  %(message)s')
            handler.setFormatter(formatter)

            logger.addHandler(handler)
        logger.info(f"Logging to {logging_path}")


    def handle(
        self,
        *,
        verbosity: int,
        queue_name: str,
        interval: float,
        batch: bool,
        backend_name: str,
            config: str,
        **options: dict,
    ) -> None:

        with open(config, "r") as f:
            config = json.load(f)
        self.configure_logging(verbosity, config["options"]["logfile"])
        cWorker = CeleryWorker.objects.get_or_create(worker_name=config["name"], worker_hostname=config["options"]["hostname"])[0]
        cWorker.worker_params = config
        cWorker.worker_info = get_system_info()
        cWorker.worker_status = "ONLINE"
        cWorker.save()

        worker = CatapultWorker(
            queue_names=queue_name.split(","),
            interval=interval,
            batch=batch,
            backend_name=backend_name,
            c_worker=cWorker
        )

        worker.start()

        if batch:
            logger.info("No more tasks to run - exiting gracefully.")