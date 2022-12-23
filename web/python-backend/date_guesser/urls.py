from django.urls import path

from . import views

urlpatterns = [
    path("items/", views.items, name="items"),
    path("", views.random_image, name="random"),
    path("showform/", views.show_form, name="form_data"),
    path("<str:item_id>/", views.show, name="show"),
]