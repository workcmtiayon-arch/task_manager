from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Achemine chaque conversation vers son consumer dédié via son identifiant.
    re_path(r"^ws/chat/(?P<conversation_id>\d+)/$", consumers.ChatConsumer.as_asgi())
]
