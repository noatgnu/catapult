from catapult.models import Analysis, CeleryTask

from celery import shared_task, Task

class AnalysisTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "FAILURE"
        task.save()
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "SUCCESS"
        task.save()
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        task = CeleryTask.objects.get(task_id=task_id)
        task.status = "RETRY"
        task.save()
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def before_start(self, task_id, args, kwargs):
        task = CeleryTask.objects.get_or_create(task_id=task_id)[0]
        task.status = "PENDING"
        task.task_name = self.name
        task.save()
        super().before_start(task_id, args, kwargs)


@shared_task(name="catapult.tasks.run_analysis", bind=True, max_retries=5, default_retry_delay=60 * 5, base=AnalysisTask)
def run_analysis(self, analysis_id: int):
    analysis = Analysis.objects.get(id=analysis_id)
    task = CeleryTask.objects.get(task_id=self.request.id)
    task.status = "RUNNING"
    task.analysis = analysis
    task.save()
    analysis.start_analysis()
    return analysis_id


@shared_task(name="catapult.tasks.run_quant", bind=True, max_retries=5, default_retry_delay=60 * 5, base=AnalysisTask)
def run_quant(self, analysis_id: int):
    analysis = Analysis.objects.get(id=analysis_id)
    task = CeleryTask.objects.create(task_id=self.request.id)
    task.analysis = analysis
    task.save()
    analysis.create_quant_file()
    return analysis_id