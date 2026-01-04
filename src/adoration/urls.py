from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.registration_view, name="registration"),
    path("delete/<str:token>/", views.delete_assignment, name="delete_assignment"),
    path("maintainer/", include("adoration.maintainer_urls")),
]
