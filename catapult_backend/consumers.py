from datetime import datetime

from channels.generic.websocket import AsyncJsonWebsocketConsumer

class JobConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.personal_id = self.scope["url_route"]["kwargs"]["personal_id"]
        await self.channel_layer.group_add(
            self.task_id,
            self.channel_name
        )
        await self.accept()
        await self.send_json({"message": f"Connected to the {self.task_id} job channel"})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.task_id,
            self.channel_name
        )

    async def receive_json(self, content):
        await self.channel_layer.group_send(
            self.task_id,
            {
                "type": "job_message",
                "message": content,
            }
        )

    async def job_message(self, event):
        content = event["message"]
        await self.send_json(content)

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.notification_type = self.scope["url_route"]["kwargs"]["notification_type"]
        self.personal_id = self.scope["url_route"]["kwargs"]["personal_id"]
        await self.channel_layer.group_add(
            self.notification_type,
            self.channel_name
        )
        await self.accept()
        await self.send_json({"message": f"Connected to the {self.notification_type} notification channel"})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_type,
            self.channel_name
        )

    async def receive_json(self, content):
        print(content)
        await self.channel_layer.group_send(
            self.notification_type,
            {
                "type": "notification_message",
                "message": content,
            }
        )

    async def notification_message(self, event):
        print(event)
        content = event["message"]
        await self.send_json(content)


class LogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.log_type = self.scope["url_route"]["kwargs"]["log_type"]
        await self.channel_layer.group_add(
            self.log_type,
            self.channel_name
        )
        await self.accept()
        await self.send_json({
            "task_id": "general",
            "hostname": "root",
            "log": f"Connected to the {self.log_type} log channel",
            "timestamp": f"{datetime.now().timestamp()}"
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.log_type,
            self.channel_name
        )

    async def receive_json(self, content):
        await self.channel_layer.group_send(
            self.log_type,
            {
                "type": "log_message",
                "message": content,
            }
        )

    async def log_message(self, event):
        content = event["message"]
        await self.send_json(content)