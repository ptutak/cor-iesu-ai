from django.urls import path

from . import views

urlpatterns = [
    path(
        "collection/<int:collection_id>/periods/",
        views.get_collection_periods,
        name="get_collection_periods",
    ),
    path(
        "collection/<int:collection_id>/maintainers/",
        views.get_collection_maintainers,
        name="get_collection_maintainers",
    ),
]
