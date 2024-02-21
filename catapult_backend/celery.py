import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catapult_backend.settings')

from catapult_backend.settings import REDIS_URL

app = Celery('catapult_backend', broker=REDIS_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

