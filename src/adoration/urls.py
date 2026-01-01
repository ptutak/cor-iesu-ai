from django.urls import path

from . import views

urlpatterns = [
    path("", views.registration_view, name="registration"),
    path("delete/<str:token>/", views.delete_assignment, name="delete_assignment"),
    path(
        "api/collection/<int:collection_id>/periods/",
        views.get_collection_periods,
        name="get_collection_periods",
    ),
]
