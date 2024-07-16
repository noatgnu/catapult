import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Callable, Optional, Union, Any

import pandas as pd
from django.utils import timezone
from django_tasks.task import P, ResultStatus
from typing_extensions import Self

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from catapult.models import Analysis, CeleryTask, CeleryWorker, File, CatapultRunConfig, ResultSummary, LogRecord

from celery import shared_task, Task
from django_tasks import Task as DjangoTask, BaseTaskBackend
from django_tasks import task as native_task
from django_tasks.task import TaskResult

from uuid import uuid4



class CatapultTaskResult(TaskResult):
    task: DjangoTask
    """The task for which this is a result"""

    id: str
    """A unique identifier for the task result"""

    status: ResultStatus
    """The status of the running task"""

    args: tuple[Any, ...]
    """The arguments to pass to the task function"""

    kwargs: dict[str, Any]
    """The keyword arguments to pass to the task function"""

    backend: str
    """The name of the backend the task will run on"""

    result: Any
    """The return value from the task"""

    def refresh(self) -> None:
        """
        Refresh the task result.
        """
        pass

class CatapultTask(DjangoTask):
    priority: int | None
    """The priority of the task"""

    func: Callable
    """The task function"""

    queue_name: str | None
    """The name of the queue the task will run on """

    backend: str
    """The name of the backend the task will run on"""

    run_after: datetime | None
    """The earliest this task will run"""

    def using(
        self,
        priority: Optional[int] = None,
        queue_name: Optional[str] = None,
        run_after: Optional[Union[datetime, timedelta]] = None,
        backend: Optional[str] = None,
    ) -> Self:
        """
        Return a new task instance with the specified attributes.
        """
        return super().using(priority, queue_name, run_after, backend)

    def enqueue(self, *args: P.args, **kwargs: P.kwargs) -> CatapultTaskResult:
        """
        Enqueue the task with the specified arguments.

        :param args:
        :param kwargs:
        :return:
        """

        if "task_id" in kwargs:
            ui = kwargs["task_id"]
            task = CeleryTask.objects.get_or_create(task_id=ui)[0]
            task.task_id = ui
        else:
            task = CeleryTask.objects.get_or_create(task_id=self.name)[0]
            task.status = "PENDING"
        task.task_name = self.name
        task.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": task.task_id,
                    "status": "PENDING",
                }
            },
        )
        kwargs["task_id"] = task.task_id
        return super().enqueue(*args, **kwargs)




    def run(self, *args: P.args, **kwargs: P.kwargs) -> Self:
        """
        Run the task with the specified arguments.

        :param args:
        :param kwargs:
        :return:
        """
        pass


class CatapultTaskBackend(BaseTaskBackend):
    task_class = CatapultTask

    def __init__(self, settings_dict: dict[str, Any]) -> None:
        """
        Any connections which need to be setup can be done here
        """
        super().__init__(settings_dict)

    @classmethod
    def validate_task(cls, task: CatapultTask) -> None:
        """
        Determine whether the provided task is one which can be executed by the backend.
        """
        pass

    def enqueue(self, task: CatapultTask, *args, **kwargs) -> CatapultTaskResult:
        """
        Queue up a task to be executed
        """
        pass


    def get_result(self, result_id: str) -> CatapultTaskResult:
        """
        Retrieve a result by its id (if one exists).
        If one doesn't, raises ResultDoesNotExist.
        """
        return super().get_result(result_id)


    def close(self) -> None:
        """
        Close any connections opened as part of the constructor
        """
        super().close()


class AnalysisTask(Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_layer = get_channel_layer()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        async_to_sync(self.channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": task_id,
                    "status": "FAILURE",
                }
            },
        )
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "FAILURE"
        task.save()
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        async_to_sync(self.channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": task_id,
                    "status": "SUCCESS",
                }
            },
        )
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "SUCCESS"
        task.save()
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        async_to_sync(self.channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": task_id,
                    "status": "RETRY",
                }
            },
        )
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "RETRY"
        task.save()
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def before_start(self, task_id, args, kwargs):
        if "task_id" in kwargs:
            ui = kwargs["task_id"]
            task = CeleryTask.objects.get_or_create(task_id=ui)[0]
            task.task_id = task_id
        else:
            task = CeleryTask.objects.get_or_create(task_id=task_id)[0]
            task.status = "PENDING"
        task.task_name = self.name
        task.save()
        async_to_sync(self.channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": task.task_id,
                    "status": "PENDING",
                }
            },
        )
        kwargs["task_id"] = task.task_id
        super().before_start(task_id, args, kwargs)

    def delay(self, *args, **kwargs):
        analysis = Analysis.objects.get(id=args[0])
        ui = "temp_" + str(uuid4())
        task = CeleryTask.objects.get_or_create(task_id=ui)[0]
        task.status = "PENDING"
        task.task_name = self.name
        task.analysis = analysis
        task.save()
        async_to_sync(self.channel_layer.group_send)(
            f"alert",
            {
                "type": "notification_message",
                "message": {
                    "task_id": ui,
                    "status": "PENDING",
                }
            },
        )
        kwargs["task_id"] = ui
        print(args)
        print(kwargs)
        task = super().delay(*args, **kwargs)
        return task


@shared_task(name="catapult.tasks.run_analysis", bind=True, max_retries=5, default_retry_delay=60 * 5, base=AnalysisTask)
def run_analysis(self, analysis_id: int, task_id: str = None):
    try:
        worker = CeleryWorker.objects.get(worker_hostname=self.request.hostname)
    except CeleryWorker.DoesNotExist:
        worker = CeleryWorker.objects.create(worker_hostname=self.request.hostname)

    analysis = Analysis.objects.get(id=analysis_id)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=self.request.id)
    async_to_sync(self.channel_layer.group_send)(
        "alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": self.request.id,
                "status": "RUNNING",
            }
        },
    )
    task.status = "RUNNING"
    task.analysis = analysis
    task.save()
    worker.tasks.add(task)
    worker.save()
    analysis.start_analysis(task_id=self.request.id, hostname=self.request.hostname)
    worker.tasks.remove(task)
    worker.save()
    return analysis_id


@shared_task(name="catapult.tasks.run_quant", bind=True, max_retries=5, default_retry_delay=60 * 5, base=AnalysisTask)
def run_quant(self, analysis_id: int, task_id: str = None):
    try:
        worker = CeleryWorker.objects.get(worker_hostname=self.request.hostname)
    except CeleryWorker.DoesNotExist:
        worker = CeleryWorker.objects.create(worker_hostname=self.request.hostname)
    analysis = Analysis.objects.get(id=analysis_id)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=self.request.id)
    async_to_sync(self.channel_layer.group_send)(
        f"alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": self.request.id,
                "status": "RUNNING",
            }
        },
    )
    task.status = "RUNNING"
    task.analysis_params = analysis.commands
    task.analysis = analysis
    task.save()
    worker.tasks.add(task)
    worker.save()
    analysis.create_quant_file(task_id=self.request.id, hostname=self.request.hostname)
    worker.tasks.remove(task)
    worker.save()
    return analysis_id

@native_task()
def native_run_quant(analysis_id: int, task_id: str = None, worker_hostname: str = None):
    analysis = Analysis.objects.get(id=analysis_id)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=task_id)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": task_id,
                "status": "RUNNING",
            }
        },
    )
    task.status = "RUNNING"
    task.analysis_params = analysis.commands
    task.analysis = analysis
    task.save()
    try:
        analysis.create_quant_file(task_id=task_id, hostname=worker_hostname)
    except Exception as e:
        task.status = "FAILURE"
        task.save()
        raise e
    return analysis_id

@native_task()
def native_run_analysis(analysis_id: int, task_id: str = None, worker_hostname: str = None):
    analysis = Analysis.objects.get(id=analysis_id)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=task_id)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": task_id,
                "status": "RUNNING",
            }
        },
    )
    task.status = "RUNNING"
    task.analysis_params = analysis.commands
    task.analysis = analysis
    task.save()
    try:
        analysis.start_analysis(task_id=task_id, hostname=worker_hostname)
    except Exception as e:
        task.status = "FAILURE"
        task.save()
        raise e

    return analysis_id

@native_task()
def calculate_meaning_of_life(task_id: str = "", worker_hostname: str = "") -> int:
    print(task_id)
    print(worker_hostname)
    return 42

@native_task()
def run_diann_worker(commands: list[str], task_id: str = "", worker_hostname: str = "", analysis_id: int = None, config_id: int = None):
    cWorker = CeleryWorker.objects.get(worker_hostname=worker_hostname)
    logging_path = cWorker.worker_params["options"]["logfile"]
    logger = logging.getLogger(f"catapult.worker{logging_path}")
    config = CatapultRunConfig.objects.get(id=config_id)
    parent_folder = os.path.dirname(config.config_file_path)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=task_id)
    analysis = Analysis.objects.get(id=analysis_id)
    task.analysis = analysis
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": task_id,
                "status": "RUNNING",
            }
        },
    )

    task.status = "RUNNING"
    task.analysis_params = json.dumps(commands)
    task.save()
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in process.stdout:
            print(line)
            output_line = line.decode("utf-8").strip()
            if output_line:
                LogRecord.objects.create(
                    task=task,
                    log=output_line.strip()
                )
                async_to_sync(channel_layer.group_send)(
                    "analysis_log", {
                        "type": "log_message",
                        "message": {
                            "task_id": task_id,
                            "log": output_line,
                            "hostname": worker_hostname,
                            "timestamp": f"{datetime.now().timestamp()}",
                        },
                    }
                )

        if analysis.generating_quant.all().count() == analysis.total_files:
            analysis.completed = True
            analysis.save()
        for file in analysis.generating_quant.all():
            analysis.generated_quant.add(file)
            analysis.generating_quant.remove(file)
        if analysis.completed:
            for file in analysis.generated_quant.all():
                file.processing = False
                file.save()
        task.status = "SUCCESS"
        task.save()
    except Exception as e:
        task.status = "FAILED"
        task.save()
        raise e
    report_stats_file = os.path.join(parent_folder, config.content["prefix"],
                                     "report.stats.tsv")
    if os.path.exists(report_stats_file):
        data = pd.read_csv(str(report_stats_file), sep="\t")
        for i, r in data.iterrows():
            file_path = r["File.Name"].replace(config.folder_watching_location.folder_path,
                                               "")
            file = File.objects.get(file_path=file_path)
            result_summary = ResultSummary.objects.filter(analysis=analysis, file=file)
            if not result_summary.exists():
                ResultSummary.objects.create(
                    analysis=analysis,
                    file=file,
                    protein_identified=r["Proteins.Identified"],
                    precursor_identified=r["Precursors.Identified"],
                    log_file=os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    )
                )
            else:
                result_summary = result_summary.first()
                if r["Proteins.Identified"] != result_summary.protein_identified or r[
                    "Precursors.Identified"] != result_summary.precursor_identified:
                    result_summary.protein_identified = r["Proteins.Identified"]
                    result_summary.precursor_identified = r["Precursors.Identified"]
                    result_summary.log_file = os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    )
                    result_summary.save()
    analysis.processing = False
    analysis.stop_time = timezone.now()
    analysis.save(update_fields=["processing", "stop_time"])
    return analysis_id

def run_diann(commands: list[str], task_id: str = "", worker_hostname: str = "", analysis_id: int = None, config_id: int = None):
    config = CatapultRunConfig.objects.get(id=config_id)
    parent_folder = os.path.dirname(config.config_file_path)
    if task_id:
        task = CeleryTask.objects.get(task_id=task_id)
    else:
        task = CeleryTask.objects.create(task_id=task_id)
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.save()
    task.analysis = analysis
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"alert",
        {
            "type": "notification_message",
            "message": {
                "task_id": task_id,
                "status": "RUNNING",
            }
        },
    )

    task.status = "RUNNING"
    task.analysis_params = json.dumps(commands)
    task.save()
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        analysis.commands = subprocess.list2cmdline(commands)
        analysis.output_folder = os.path.join(parent_folder, config.content["prefix"])
        analysis.save(update_fields=["commands"])
        for line in process.stdout:
            line = line.decode("utf-8").strip()
            if line:
                LogRecord.objects.create(
                    task=task,
                    log=line
                )

        analysis.processing = False
        analysis.save(update_fields=["processing"])
        if analysis.generating_quant.all().count() == analysis.total_files:
            analysis.completed = True
            analysis.save()

        for file in analysis.generating_quant.all():
            analysis.generated_quant.add(file)
            analysis.generating_quant.remove(file)
        if analysis.completed:
            for file in analysis.generated_quant.all():
                file.processing = False
                file.save()
        task.status = "SUCCESS"
        task.save()
    except Exception as e:
        task.status = "FAILED"
        task.save()
        analysis.processing = False
        analysis.save(update_fields=["processing"])
        raise e
    report_stats_file = os.path.join(parent_folder, config.content["prefix"],
                                     "report.stats.tsv")
    if os.path.exists(report_stats_file):
        data = pd.read_csv(str(report_stats_file), sep="\t")
        for i, r in data.iterrows():
            file_path = r["File.Name"].replace(config.folder_watching_location.folder_path,
                                               "")
            file = File.objects.get(file_path=file_path)
            result_summary = ResultSummary.objects.filter(analysis=analysis, file=file)
            if not result_summary.exists():
                ResultSummary.objects.create(
                    analysis=analysis,
                    file=file,
                    protein_identified=r["Proteins.Identified"],
                    precursor_identified=r["Precursors.Identified"],
                    log_file=os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    )
                )
            else:
                result_summary = result_summary.first()
                if r["Proteins.Identified"] != result_summary.protein_identified or r["Precursors.Identified"] != result_summary.precursor_identified:
                    result_summary.protein_identified = r["Proteins.Identified"]
                    result_summary.precursor_identified = r["Precursors.Identified"]
                    result_summary.log_file = os.path.join(
                        str(parent_folder.replace(config.folder_watching_location.folder_path, "")),
                        config.content["prefix"],
                        "report.stats.tsv"
                    )
                    result_summary.save()
    analysis.processing = False
    analysis.stop_time = timezone.now()
    analysis.save(update_fields=["processing", "stop_time"])
    return analysis_id


