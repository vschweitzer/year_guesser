from django.urls import path

from . import views

urlpatterns = [
    path("", views.items, name="items"),
    path("<str:item_id>/", views.show, name="show"),
]