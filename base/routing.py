from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/whiteboard/(?P<room_id>\w+)/$', consumers.WhiteboardConsumer.as_asgi()),
]