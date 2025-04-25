from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    #re_path(r'ws/whiteboard/(?P<room_id>\w+)/$', consumers.WhiteboardConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<reservation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/webrtc/(?P<reservation_id>\d+)/$', consumers.WebRTCSignalConsumer.as_asgi()),

]