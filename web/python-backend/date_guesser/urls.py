from django.urls import path

from . import views

urlpatterns = [
    path("", views.items, name="items"),
    path("showform/", views.show_form, name="form_data"),
    path("<str:item_id>/", views.show, name="show"),
]