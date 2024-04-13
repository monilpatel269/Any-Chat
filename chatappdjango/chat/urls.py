from django.urls import path

from chat import views

app_name = 'chat'

urlpatterns = [
	path('', views.private_chat_room_view, name='private_chat_room'),
	path('create_or_return_private_chat/', views.create_or_return_private_chat, name='create_or_return_private_chat'),
]