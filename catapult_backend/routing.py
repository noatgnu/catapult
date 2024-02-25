from django.urls import re_path

from catapult_backend.consumers import JobConsumer, NotificationConsumer, LogConsumer

websocket_urlpatterns = [
    re_path(r'ws/jobs/(?P<task_id>[\w\-]+)/(?P<personal_id>[\w\-]+)/$', JobConsumer.as_asgi()),
    re_path(r'ws/notification/(?P<notification_type>[\w\-]+)/(?P<personal_id>[\w\-]+)/$', NotificationConsumer.as_asgi()),
    re_path(r'ws/log/(?P<log_type>[\w\-]+)/$', LogConsumer.as_asgi()),
]