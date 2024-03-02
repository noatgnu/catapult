import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catapult_backend.settings')

from catapult_backend.settings import REDIS_URL

from celery.signals import worker_shutting_down, celeryd_after_setup


@celeryd_after_setup.connect
def worker_started_handler(sender, instance, **kwargs):
    from catapult.models import CeleryWorker
    worker, created = CeleryWorker.objects.get(worker_hostname=os.environ.get('WORKER_HOSTNAME'))
    worker.worker_os = os.name
    worker.worker_status = 'ONLINE'
    worker.save()

@worker_shutting_down.connect
def worker_shutting_down_handler(sig, how, exitcode, **kwargs):
    from catapult.models import CeleryWorker
    worker = CeleryWorker.objects.get(worker_hostname=os.environ.get('WORKER_HOSTNAME'))
    worker.worker_status = 'OFFLINE'
    worker.save()


app = Celery('catapult_backend', broker=REDIS_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_default_queue = 'default'
app.autodiscover_tasks()


