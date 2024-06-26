import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from chat.consumers import ChatConsumer
from public_chat.consumers import PublicChatConsumer
from notification.consumers import NotificationConsumer

application = ProtocolTypeRouter(
    {
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    [
                        path("", NotificationConsumer.as_asgi()),
                        path("public_chat/<room_id>/", PublicChatConsumer.as_asgi()),
                        path('chat/<room_id>/', ChatConsumer.as_asgi()),
                    ]
                )
            )
        ),
    }
)
