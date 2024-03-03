from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from catapult.models import Analysis, CeleryTask, CeleryWorker

from celery import shared_task, Task

from uuid import uuid4

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