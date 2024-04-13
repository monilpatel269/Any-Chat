from django.urls import path
from django.conf import settings
from friend import views

app_name = "friend"

urlpatterns = [
    path('list/<user_id>', views.friends_list_view, name='list'),
    path("friend_request/",views.send_friend_request, name="friend_request"),
    path("friend_request/<user_id>/",views.friend_requests, name="friend_requests"),
    path("friend_remove/",views.remove_friend, name="remove_friend"),
    path("friend_request_cancel/",views.cancel_friend_request, name="friend_request_cancel"),
    path("accept_friend_request/<friend_request_id>/",views.accept_friend_request, name="friend_request_accept"),
    path("decline_friend_request/<friend_request_id>/",views.decline_friend_request, name="friend_request_decline"),
]