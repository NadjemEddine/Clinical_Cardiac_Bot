from django.urls import path

from . import consumers , consumers_welcome, consumers_HVR, consumers_imaging

websocket_urlpatterns = [
    path("ws/chat/<str:room_name>/", consumers.ChatConsumer.as_asgi()),
    path("ws/welcomeChat/<str:room_name>/", consumers_welcome.ChatConsumer.as_asgi()),
    path("ws/EHR/<str:room_name>/", consumers_HVR.HVRChatConsumer.as_asgi()),
    path("ws/imaging/<str:room_name>/", consumers_imaging.ImagingConsumer.as_asgi()),

]