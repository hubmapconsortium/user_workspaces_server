import json
import threading

import websocket
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from . import models


class PassthroughConsumer(WebsocketConsumer):
    def connect(self):
        hostname = self.scope["url_route"]["kwargs"]["hostname"]
        job_id = self.scope["url_route"]["kwargs"]["job_id"]
        job_model = models.Job.objects.get(pk=job_id)
        connection_details = job_model.job_details["current_job_details"].get("proxy_details", {})
        port = connection_details.get("port", "")
        headers = {}
        for item in self.scope["headers"]:
            headers[item[0].decode("UTF-8")] = item[1].decode("UTF-8")

        # Define WebSocket callback functions
        def ws_message(ws, message):
            self.send(message)

        # Start a new thread for the WebSocket interface
        self.ws = websocket.WebSocketApp(
            f'ws://{hostname}:{port}{self.scope["path"]}?{self.scope["query_string"].decode("UTF-8")}',
            cookie=headers["cookie"],
            on_message=ws_message,
        )
        self.response_ws_thread = threading.Thread(target=self.ws.run_forever)
        self.response_ws_thread.start()

        self.accept()

    def disconnect(self, close_code):
        self.ws.close()
        self.response_ws_thread.join(1)

    # Receive message from WebSocket
    def receive(self, text_data=None, bytes_data=None):
        self.ws.send(text_data)


class JobStatusConsumer(WebsocketConsumer):
    def connect(self):
        job_id = self.scope["url_route"]["kwargs"]["job_id"]
        self.room_group_name = f"job_status_{job_id}"

        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    def receive(self, text_data=None, bytes_data=None):
        # TODO: What would a client want to get from this.
        pass

    # Receive message from room group
    def job_status_update(self, event):
        job_details = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps(job_details))
