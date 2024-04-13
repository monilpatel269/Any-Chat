from django.urls import path
from account import views

app_name = "account"

urlpatterns = [
    path('<user_id>/',views.account_view,name="view"),
    path('<user_id>/edit/',views.edit_account_view,name="edit"),
    path('<user_id>/edit/crop_image/',views.crop_image,name="crop_image"),
]