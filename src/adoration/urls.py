from django.urls import path

from . import views

urlpatterns = [
    path("", views.registration_view, name="registration"),
    path("delete/<str:token>/", views.delete_assignment, name="delete_assignment"),
]
