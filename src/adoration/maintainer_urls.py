"""
URL patterns for the maintainer panel.

This module defines URL patterns for maintainer-specific views including
collection management, period management, and user promotion.
"""

from django.urls import path

from . import maintainer_views

app_name = "maintainer"

urlpatterns = [
    # Dashboard
    path("", maintainer_views.MaintainerDashboardView.as_view(), name="dashboard"),
    # Collection management
    path(
        "collections/",
        maintainer_views.CollectionListView.as_view(),
        name="collection_list",
    ),
    path(
        "collections/create/",
        maintainer_views.CollectionCreateView.as_view(),
        name="collection_create",
    ),
    path(
        "collections/<int:pk>/",
        maintainer_views.CollectionDetailView.as_view(),
        name="collection_detail",
    ),
    path(
        "collections/<int:pk>/edit/",
        maintainer_views.CollectionUpdateView.as_view(),
        name="collection_edit",
    ),
    # Period management
    path("periods/", maintainer_views.PeriodListView.as_view(), name="period_list"),
    path(
        "periods/create/",
        maintainer_views.PeriodCreateView.as_view(),
        name="period_create",
    ),
    path(
        "periods/<int:pk>/edit/",
        maintainer_views.PeriodUpdateView.as_view(),
        name="period_edit",
    ),
    # Period-Collection assignment
    path(
        "assign-period/",
        maintainer_views.assign_period_to_collection,
        name="assign_period",
    ),
    path(
        "remove-period/",
        maintainer_views.remove_period_from_collection,
        name="remove_period",
    ),
    # Assignment management
    path(
        "assignments/",
        maintainer_views.AssignmentListView.as_view(),
        name="assignment_list",
    ),
    # User promotion
    path(
        "promote-users/",
        maintainer_views.UserPromotionView.as_view(),
        name="user_promotion",
    ),
    path(
        "promote-user/",
        maintainer_views.promote_user_to_maintainer,
        name="promote_user",
    ),
]
