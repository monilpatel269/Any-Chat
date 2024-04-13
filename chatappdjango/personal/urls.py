from django.urls import path, include
from personal import views

urlpatterns = [
    path("", views.home_screen_view, name="home"),
]
