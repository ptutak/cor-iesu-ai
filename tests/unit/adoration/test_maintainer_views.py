"""
Unit tests for maintainer views.

This module contains comprehensive tests for all maintainer panel views,
including authentication, permissions, CRUD operations, and AJAX endpoints.
"""

import json

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.test import Client, TestCase
from django.urls import reverse

from adoration.models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


@pytest.fixture
def maintainer_with_permissions(maintainer_user, maintainer, db):
    """Create a maintainer user with proper permissions."""
    # Add user to maintainer group
    maintainer_group, created = Group.objects.get_or_create(name="Maintainers")
    maintainer_user.groups.add(maintainer_group)
    maintainer_user.user_permissions.add(*maintainer_group.permissions.all())
    return maintainer_user


@pytest.mark.django_db
class TestMaintainerRequiredMixin:
    """Test cases for MaintainerRequiredMixin."""

    def test_unauthenticated_user_redirected_to_login(self, client):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("maintainer:dashboard")
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response.url

    def test_authenticated_non_maintainer_gets_permission_denied(self, client, django_user_model):
        """Test that authenticated non-maintainers get permission denied."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        url = reverse("maintainer:dashboard")
        response = client.get(url)
        assert response.status_code == 403

    def test_authenticated_maintainer_has_access(self, client, maintainer_user, maintainer):
        """Test that authenticated maintainers can access views."""
        client.force_login(maintainer_user)

        url = reverse("maintainer:dashboard")
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestMaintainerDashboardView:
    """Test cases for MaintainerDashboardView."""

    def test_dashboard_displays_correct_statistics(
        self,
        client,
        maintainer_with_permissions,
        maintainer,
        collection,
        period_collection,
    ):
        """Test that dashboard displays correct statistics."""
        client.force_login(maintainer_with_permissions)

        # Create collection maintainer relationship
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create some assignments
        for i in range(3):
            assignment = PeriodAssignment.create_with_email(
                email=f"test{i}@example.com", period_collection=period_collection
            )
            assignment.save()

        url = reverse("maintainer:dashboard")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["total_collections"] == 1
        assert response.context["total_assignments"] == 3
        assert response.context["maintainer"] == maintainer

    def test_dashboard_shows_only_managed_collections(
        self, client, maintainer_with_permissions, maintainer, collection
    ):
        """Test that dashboard only shows collections managed by the maintainer."""
        client.force_login(maintainer_with_permissions)

        # Create another collection not managed by this maintainer
        other_collection = Collection.objects.create(name="Other Collection", description="Not managed", enabled=True)

        # Only assign maintainer to first collection
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:dashboard")
        response = client.get(url)

        collections = response.context["collections"]
        assert collections.count() == 1
        assert collection in collections
        assert other_collection not in collections


@pytest.mark.django_db
class TestCollectionListView:
    """Test cases for CollectionListView."""

    def test_collection_list_shows_only_managed_collections(
        self, client, maintainer_with_permissions, maintainer, collection
    ):
        """Test that collection list only shows managed collections."""
        client.force_login(maintainer_with_permissions)

        # Create collections
        managed_collection = collection
        other_collection = Collection.objects.create(name="Other Collection", description="Not managed", enabled=True)

        CollectionMaintainer.objects.create(collection=managed_collection, maintainer=maintainer)

        url = reverse("maintainer:collection_list")
        response = client.get(url)

        assert response.status_code == 200
        collections = response.context["collections"]
        assert collections.count() == 1
        assert managed_collection in collections
        assert other_collection not in collections

    def test_empty_collection_list(self, client, maintainer_with_permissions):
        """Test collection list when maintainer has no collections."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:collection_list")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["collections"].count() == 0


@pytest.mark.django_db
class TestCollectionCreateView:
    """Test cases for CollectionCreateView."""

    def test_collection_create_get(self, client, maintainer_with_permissions):
        """Test GET request to collection create view."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:collection_create")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_collection_create_post_valid(self, client, maintainer_with_permissions, maintainer):
        """Test POST request with valid data creates collection and assigns maintainer."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:collection_create")
        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en", "pl"],
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 302  # Redirect after success

        # Check collection was created
        collection = Collection.objects.get(name="Test Collection")
        assert collection.description == "Test Description"
        assert collection.enabled is True
        assert collection.available_languages == ["en", "pl"]

        # Check maintainer was automatically assigned
        assert CollectionMaintainer.objects.filter(collection=collection, maintainer=maintainer).exists()

    def test_collection_create_post_invalid(self, client, maintainer_with_permissions):
        """Test POST request with invalid data returns form with errors."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:collection_create")
        form_data = {
            "name": "",  # Required field missing
            "description": "Test Description",
            "enabled": True,
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 200  # Form redisplayed with errors
        assert "form" in response.context
        assert response.context["form"].errors


@pytest.mark.django_db
class TestCollectionUpdateView:
    """Test cases for CollectionUpdateView."""

    def test_collection_update_get(self, client, maintainer_user, maintainer, collection):
        """Test GET request to collection update view."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:collection_edit", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == collection

    def test_collection_update_post_valid(self, client, maintainer_user, maintainer, collection):
        """Test POST request with valid data updates collection."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:collection_edit", kwargs={"pk": collection.pk})
        form_data = {
            "name": "Updated Collection",
            "description": "Updated Description",
            "enabled": False,
            "available_languages": ["en"],
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 302  # Redirect after success

        collection.refresh_from_db()
        assert collection.name == "Updated Collection"
        assert collection.description == "Updated Description"
        assert collection.enabled is False
        assert collection.available_languages == ["en"]

    def test_collection_update_not_managed_collection_404(self, client, maintainer_with_permissions, collection):
        """Test that maintainer cannot edit collections they don't manage."""
        client.force_login(maintainer_with_permissions)

        # Create a separate collection that this maintainer doesn't manage
        unmanaged_collection = Collection.objects.create(
            name="Unmanaged Collection",
            description="Collection not managed by this maintainer",
            enabled=True,
            available_languages=["en"],
        )

        url = reverse("maintainer:collection_edit", kwargs={"pk": unmanaged_collection.pk})
        response = client.get(url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestCollectionDetailView:
    """Test cases for CollectionDetailView."""

    def test_collection_detail_get(self, client, maintainer_user, maintainer, collection):
        """Test GET request to collection detail view."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:collection_detail", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == collection

    def test_collection_detail_with_periods_and_assignments(
        self, client, maintainer_user, maintainer, collection, period, period_collection
    ):
        """Test collection detail shows periods and assignments correctly."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:collection_detail", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 200
        period_collections = response.context["period_collections"]
        assert period_collections.count() == 1
        assert response.context["total_assignments"] == 1

    def test_collection_detail_not_managed_collection_404(self, client, maintainer_with_permissions, collection):
        """Test that maintainer cannot view details of collections they don't manage."""
        client.force_login(maintainer_with_permissions)

        # Create a separate collection that this maintainer doesn't manage
        unmanaged_collection = Collection.objects.create(
            name="Unmanaged Collection",
            description="Collection not managed by this maintainer",
            enabled=True,
            available_languages=["en"],
        )

        url = reverse("maintainer:collection_detail", kwargs={"pk": unmanaged_collection.pk})
        response = client.get(url)

        assert response.status_code == 404


class TestCollectionDeleteView:
    """Test cases for CollectionDeleteView."""

    def test_collection_delete_get(self, client, maintainer_user, maintainer, collection):
        """Test GET request to collection delete view."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:collection_delete", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == collection
        assert "total_periods" in response.context
        assert "total_assignments" in response.context

    def test_collection_delete_post_success(self, client, maintainer_user, maintainer, collection):
        """Test POST request successfully deletes collection."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:collection_delete", kwargs={"pk": collection.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("maintainer:collection_list")

        # Verify collection was deleted
        assert not Collection.objects.filter(pk=collection.pk).exists()

    def test_collection_delete_with_assignments_cascades(
        self,
        client,
        maintainer_user,
        maintainer,
        collection,
        period,
        period_collection,
    ):
        """Test deleting collection with assignments cascades properly."""
        client.force_login(maintainer_user)

        # Create collection maintainer relationship
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:collection_delete", kwargs={"pk": collection.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("maintainer:collection_list")

        # Verify collection and related data was deleted (cascades)
        assert not Collection.objects.filter(pk=collection.pk).exists()
        assert not PeriodAssignment.objects.filter(pk=assignment.pk).exists()
        assert not PeriodCollection.objects.filter(pk=period_collection.pk).exists()

    def test_collection_delete_not_managed_collection_404(self, client, maintainer_with_permissions, collection):
        """Test that maintainer cannot delete collections they don't manage."""
        client.force_login(maintainer_with_permissions)

        # Don't create collection maintainer relationship
        # so this collection is not managed by the maintainer

        url = reverse("maintainer:collection_delete", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 404


class TestPeriodListView:
    """Test cases for PeriodListView."""

    def test_period_list_shows_all_periods(self, client, maintainer_with_permissions, maintainer, period):
        """Test that period list shows maintainer's assigned periods."""
        client.force_login(maintainer_with_permissions)

        # Create maintainer-period relationships (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Create another period and assign to maintainer
        another_period = Period.objects.create(name="Another Period", description="Another description")
        MaintainerPeriod.objects.create(maintainer=maintainer, period=another_period)

        url = reverse("maintainer:period_list")
        response = client.get(url)

        assert response.status_code == 200
        periods = response.context["periods"]
        assert periods.count() == 2

    def test_period_list_empty(self, client, maintainer_with_permissions):
        """Test period list when no periods exist."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_list")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["periods"].count() == 0


@pytest.mark.django_db
class TestPeriodCreateView:
    """Test cases for PeriodCreateView."""

    def test_period_create_get(self, client, maintainer_with_permissions):
        """Test GET request to period create view."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_create")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context

    def test_period_create_post_valid(self, client, maintainer_with_permissions):
        """Test POST request with valid data creates period."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_create")
        form_data = {
            "name": "06:00 - 07:00",
            "description": "Morning prayer period",
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 302  # Redirect after success

        period = Period.objects.get(name="06:00 - 07:00")
        assert period.description == "Morning prayer period"

    def test_period_create_post_invalid(self, client, maintainer_with_permissions):
        """Test POST request with invalid data shows form errors."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_create")
        form_data = {
            "name": "",  # Required field missing
            "description": "Test Description",
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 200  # Form redisplayed with errors
        assert "form" in response.context
        assert response.context["form"].errors


@pytest.mark.django_db
class TestPeriodUpdateView:
    """Test cases for PeriodUpdateView."""

    def test_period_update_get(self, client, maintainer_with_permissions, period):
        """Test GET request to period update view."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_edit", kwargs={"pk": period.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == period

    def test_period_update_post_valid(self, client, maintainer_with_permissions, period):
        """Test POST request with valid data updates period."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_edit", kwargs={"pk": period.pk})
        form_data = {
            "name": "Updated Period",
            "description": "Updated Description",
        }

        response = client.post(url, data=form_data)

        assert response.status_code == 302  # Redirect after success

        period.refresh_from_db()
        assert period.name == "Updated Period"
        assert period.description == "Updated Description"


class TestPeriodDeleteView:
    """Test cases for PeriodDeleteView."""

    def test_period_delete_get(self, client, maintainer_with_permissions, maintainer, period):
        """Test GET request to period delete view shows confirmation page."""
        client.force_login(maintainer_with_permissions)

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:period_delete", kwargs={"pk": period.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["period"] == period
        assert "total_collections" in response.context
        assert "total_assignments" in response.context

    def test_period_delete_post_success(self, client, maintainer_with_permissions, maintainer):
        """Test POST request successfully removes period from maintainer management."""
        client.force_login(maintainer_with_permissions)

        # Create a new period just for this test to avoid fixture conflicts
        from adoration.models import MaintainerPeriod, Period

        period = Period.objects.create(name="Test Delete Period", description="For testing deletion")

        # Create maintainer-period relationship (required for new functionality)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:period_delete", kwargs={"pk": period.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("maintainer:period_list")

        # Check maintainer-period relationship was removed, but period still exists
        assert not MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()
        assert Period.objects.filter(pk=period.pk).exists()

    def test_period_delete_with_assignments_cascades(
        self, client, maintainer_with_permissions, period, collection, maintainer
    ):
        """Test that removing period fails when assignments exist."""
        client.force_login(maintainer_with_permissions)

        # Create collection maintainer relationship
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Create period collection and assignment
        period_collection = PeriodCollection.objects.create(collection=collection, period=period)
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:period_delete", kwargs={"pk": period.pk})
        response = client.post(url)

        assert response.status_code == 302

        # Check that nothing was deleted because assignments exist
        assert Period.objects.filter(pk=period.pk).exists()
        assert PeriodCollection.objects.filter(pk=period_collection.pk).exists()
        assert PeriodAssignment.objects.filter(pk=assignment.pk).exists()
        assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_period_delete_requires_permission(self, client, django_user_model, period):
        """Test that period delete requires proper permission."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        url = reverse("maintainer:period_delete", kwargs={"pk": period.pk})
        response = client.get(url)
        assert response.status_code == 403


class TestAssignPeriodToCollection:
    """Test cases for assign_period_to_collection AJAX view."""

    def test_assign_period_success(self, client, maintainer_with_permissions, maintainer, collection, period):
        """Test successful period assignment."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:assign_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "assigned" in json_data["message"].lower()

        # Check that period-collection relationship was created
        assert PeriodCollection.objects.filter(collection=collection, period=period).exists()

    def test_assign_period_already_assigned(self, client, maintainer_with_permissions, maintainer, collection, period):
        """Test assignment when period is already assigned."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create the relationship first
        PeriodCollection.objects.create(collection=collection, period=period)

        url = reverse("maintainer:assign_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "already assigned" in json_data["error"].lower()

    def test_assign_period_no_access_to_collection(self, client, maintainer_with_permissions, collection, period):
        """Test assigning period to collection maintainer doesn't manage."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "not found" in json_data["error"].lower()

    def test_assign_period_missing_data(self, client, maintainer_with_permissions):
        """Test assignment with missing data returns error."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period")
        data = {
            "collection_id": "",  # Missing
            "period_id": "1",
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "missing" in json_data["error"].lower()

    def test_assign_period_invalid_method(self, client, maintainer_with_permissions):
        """Test assignment with invalid HTTP method."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period")
        response = client.get(url)  # Should be POST

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "invalid method" in json_data["error"].lower()

    def test_assign_period_non_maintainer(self, client, django_user_model, collection, period):
        """Test assignment by non-maintainer returns error."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        url = reverse("maintainer:assign_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 403


@pytest.mark.django_db
class TestRemovePeriodFromCollection:
    """Test cases for remove_period_from_collection AJAX view."""

    def test_remove_period_success(
        self,
        client,
        maintainer_with_permissions,
        maintainer,
        collection,
        period,
        period_collection,
    ):
        """Test successful period removal from collection."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:remove_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert not PeriodCollection.objects.filter(id=period_collection.id).exists()
        assert "removed" in json_data["message"].lower()

        # Check that period-collection relationship was removed
        assert not PeriodCollection.objects.filter(collection=collection, period=period).exists()

    def test_remove_period_with_assignments_fails(
        self,
        client,
        maintainer_with_permissions,
        maintainer,
        collection,
        period,
        period_collection,
    ):
        """Test removing period fails when assignments exist."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:remove_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "active assignments" in json_data["error"].lower()
        assert PeriodCollection.objects.filter(id=period_collection.id).exists()

    def test_remove_period_not_assigned(self, client, maintainer_with_permissions, maintainer, collection, period):
        """Test removing period that's not assigned to maintainer."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = reverse("maintainer:remove_period")
        data = {
            "collection_id": collection.id,
            "period_id": period.id,
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "access denied" in json_data["error"].lower()


@pytest.mark.django_db
class TestPromoteUserToMaintainer:
    """Test cases for promote_user_to_maintainer AJAX view."""

    def test_promote_user_success(self, client, maintainer_user, django_user_model):
        """Test successful user promotion to maintainer."""
        # Add required permission to user
        from django.contrib.auth.models import Permission

        perm = Permission.objects.get(codename="add_maintainer")
        maintainer_user.user_permissions.add(perm)

        client.force_login(maintainer_user)

        # Create a regular user
        regular_user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )

        url = reverse("maintainer:promote_user")
        data = {
            "user_id": regular_user.id,
            "country": "Test Country",
            "phone_number": "+1234567890",
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "promoted" in json_data["message"].lower()

        # Check maintainer was created
        assert Maintainer.objects.filter(user=regular_user).exists()
        maintainer = Maintainer.objects.get(user=regular_user)
        assert maintainer.country == "Test Country"
        assert maintainer.phone_number == "+1234567890"

        # Check user was added to maintainer group
        maintainer_group = Group.objects.get(name="Maintainers")
        assert regular_user.groups.filter(id=maintainer_group.id).exists()

    def test_promote_user_already_maintainer(self, client, maintainer_user, maintainer):
        """Test promoting user who is already a maintainer returns error."""
        # Add required permission to user
        from django.contrib.auth.models import Permission

        perm = Permission.objects.get(codename="add_maintainer")
        maintainer_user.user_permissions.add(perm)

        client.force_login(maintainer_user)

        url = reverse("maintainer:promote_user")
        data = {
            "user_id": maintainer_user.id,
            "country": "Test Country",
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "already a maintainer" in json_data["error"].lower()

    def test_promote_user_no_email(self, client, maintainer_user, django_user_model):
        """Test promoting user without email returns error."""
        # Add required permission to user
        from django.contrib.auth.models import Permission

        perm = Permission.objects.get(codename="add_maintainer")
        maintainer_user.user_permissions.add(perm)

        client.force_login(maintainer_user)

        # Create user without email
        user_no_email = django_user_model.objects.create_user(username="no_email", password="testpass123")
        user_no_email.email = ""
        user_no_email.save()

        url = reverse("maintainer:promote_user")
        data = {
            "user_id": user_no_email.id,
            "country": "Test Country",
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "email address" in json_data["error"].lower()

    def test_promote_user_missing_user_id(self, client, maintainer_user):
        """Test promotion with missing user ID returns error."""
        # Add required permission to user
        from django.contrib.auth.models import Permission

        perm = Permission.objects.get(codename="add_maintainer")
        maintainer_user.user_permissions.add(perm)

        client.force_login(maintainer_user)

        url = reverse("maintainer:promote_user")
        data = {
            "country": "Test Country",
        }

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "missing user id" in json_data["error"].lower()


@pytest.mark.django_db
class TestAssignmentListView:
    """Test cases for AssignmentListView."""

    def test_assignment_list_shows_only_managed_assignments(
        self, client, maintainer_user, maintainer, collection, period_collection
    ):
        """Test that assignment list shows only assignments for managed collections."""
        client.force_login(maintainer_user)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create assignment for managed collection
        managed_assignment = PeriodAssignment.create_with_email(
            email="managed@example.com", period_collection=period_collection
        )
        managed_assignment.save()

        # Create assignment for unmanaged collection
        other_collection = Collection.objects.create(name="Other Collection", enabled=True)
        other_period = Period.objects.create(name="Other Period")
        other_pc = PeriodCollection.objects.create(collection=other_collection, period=other_period)
        other_assignment = PeriodAssignment.create_with_email(email="other@example.com", period_collection=other_pc)
        other_assignment.save()

        url = reverse("maintainer:assignment_list")
        response = client.get(url)

        assert response.status_code == 200
        assignments = response.context["assignments"]
        assert assignments.count() == 1
        assert managed_assignment in assignments
        assert other_assignment not in assignments


@pytest.mark.django_db
class TestUserPromotionView:
    """Test cases for UserPromotionView."""

    def test_user_promotion_list_excludes_maintainers(
        self, client, maintainer_with_permissions, maintainer, django_user_model
    ):
        """Test that user promotion list excludes existing maintainers."""
        client.force_login(maintainer_with_permissions)

        # Create regular user
        regular_user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )

        url = reverse("maintainer:user_promotion")
        response = client.get(url)

        assert response.status_code == 200
        users = response.context["users"]
        assert regular_user in users
        assert maintainer_with_permissions not in users  # Maintainer should be excluded

    def test_user_promotion_search_functionality(self, client, maintainer_with_permissions, django_user_model):
        """Test search functionality in user promotion view."""
        client.force_login(maintainer_with_permissions)

        # Create users
        user1 = django_user_model.objects.create_user(
            username="john_doe", email="john@example.com", password="testpass123"
        )
        user2 = django_user_model.objects.create_user(
            username="jane_smith", email="jane@example.com", password="testpass123"
        )

        url = reverse("maintainer:user_promotion")
        response = client.get(url, {"search": "john"})

        assert response.status_code == 200
        users = list(response.context["users"])
        assert user1 in users
        assert user2 not in users
        assert response.context["search_query"] == "john"


@pytest.mark.django_db
class TestMaintainerViewPermissions:
    """Test permission requirements for maintainer views."""

    def test_views_require_maintainer_permission(self, client, django_user_model):
        """Test that maintainer views require proper permissions."""
        # Create user without maintainer permissions
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        # Test dashboard specifically - it should return 403
        url = reverse("maintainer:dashboard")
        response = client.get(url)
        assert response.status_code == 403

    def test_ajax_views_require_permissions(self, client, django_user_model, collection, period):
        """Test that AJAX views require proper permissions."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        # Test assign period (should fail on permission check)
        url = reverse("maintainer:assign_period")
        response = client.post(url, {"collection_id": collection.id, "period_id": period.id})
        assert response.status_code == 403

        # Test promote user (should fail on permission check)
        url = reverse("maintainer:promote_user")
        response = client.post(url, {"user_id": user.id})
        assert response.status_code == 403


class TestDeleteAssignment:
    """Test cases for delete_assignment AJAX view."""

    def test_delete_assignment_success(
        self,
        client,
        maintainer_with_permissions,
        maintainer,
        collection,
        period_collection,
    ):
        """Test successful assignment deletion."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:delete_assignment", kwargs={"assignment_id": assignment.id})
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "deleted successfully" in json_data["message"].lower()

        # Verify assignment was deleted
        assert not PeriodAssignment.objects.filter(id=assignment.id).exists()

    def test_delete_assignment_not_managed_collection(
        self, client, maintainer_with_permissions, collection, period_collection
    ):
        """Test deletion fails for assignments in unmanaged collections."""
        client.force_login(maintainer_with_permissions)

        # Don't create collection maintainer relationship
        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:delete_assignment", kwargs={"assignment_id": assignment.id})
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "error" in json_data

    def test_delete_assignment_invalid_method(
        self,
        client,
        maintainer_with_permissions,
        maintainer,
        collection,
        period_collection,
    ):
        """Test deletion fails with GET request."""
        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:delete_assignment", kwargs={"assignment_id": assignment.id})
        response = client.get(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "invalid method" in json_data["error"].lower()

    def test_delete_assignment_non_maintainer(self, client, django_user_model, collection, period_collection):
        """Test deletion by non-maintainer returns permission denied."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:delete_assignment", kwargs={"assignment_id": assignment.id})
        response = client.post(url)

        assert response.status_code == 403


# Create simple mock templates to avoid template not found errors
@pytest.fixture(autouse=True)
def mock_templates(settings):
    """Mock templates for maintainer views."""
    import os
    import tempfile

    # Create temporary template directory
    temp_dir = tempfile.mkdtemp()
    template_dir = os.path.join(temp_dir, "adoration", "maintainer")
    os.makedirs(template_dir, exist_ok=True)

    # Create simple templates
    templates = {
        "assignment_list.html": "{% extends 'adoration/maintainer/base.html' %}",
        "user_promotion.html": "{% extends 'adoration/maintainer/base.html' %}",
    }

    for template_name, content in templates.items():
        with open(os.path.join(template_dir, template_name), "w") as f:
            f.write(content)

    settings.TEMPLATES[0]["DIRS"].insert(0, temp_dir)


@pytest.mark.django_db
class TestAssignPeriodToMaintainer:
    """Test cases for assign_period_to_maintainer AJAX view."""

    def test_assign_period_to_maintainer_success(self, client, maintainer_with_permissions, maintainer, period):
        """Test successful period assignment to maintainer."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period_to_maintainer")
        data = {"period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "assigned to you successfully" in json_data["message"]

        # Verify relationship was created
        from adoration.models import MaintainerPeriod

        assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_assign_period_to_maintainer_with_name(self, client, maintainer_with_permissions, maintainer):
        """Test period assignment by name when period doesn't exist."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period_to_maintainer")
        data = {"period_name": "New Period"}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

        # Verify period was created and assigned
        from adoration.models import MaintainerPeriod, Period

        period = Period.objects.get(name="New Period")
        assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_assign_period_already_assigned(self, client, maintainer_with_permissions, maintainer, period):
        """Test assigning period that's already assigned to maintainer."""
        from adoration.models import MaintainerPeriod

        client.force_login(maintainer_with_permissions)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:assign_period_to_maintainer")
        data = {"period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "already assigned" in json_data["error"]

    def test_assign_period_missing_data(self, client, maintainer_with_permissions):
        """Test assignment with missing data returns error."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_period_to_maintainer")
        data = {}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "missing" in json_data["error"].lower()


@pytest.mark.django_db
class TestRemovePeriodFromMaintainer:
    """Test cases for remove_period_from_maintainer AJAX view."""

    def test_remove_period_from_maintainer_success(self, client, maintainer_with_permissions, maintainer, period):
        """Test successful period removal from maintainer."""
        from adoration.models import MaintainerPeriod

        client.force_login(maintainer_with_permissions)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:remove_period_from_maintainer")
        data = {"period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "removed from your management" in json_data["message"]

        # Verify relationship was removed
        assert not MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_remove_period_with_assignments(
        self, client, maintainer_with_permissions, maintainer, collection, period, period_collection
    ):
        """Test removing period that has active assignments."""
        from adoration.models import MaintainerPeriod

        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Create assignment
        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        url = reverse("maintainer:remove_period_from_maintainer")
        data = {"period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "active assignments" in json_data["error"]

    def test_remove_period_not_assigned(self, client, maintainer_with_permissions, period):
        """Test removing period that's not assigned to maintainer."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:remove_period_from_maintainer")
        data = {"period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "not assigned to you" in json_data["error"]


@pytest.mark.django_db
class TestModifiedPeriodViews:
    """Test cases for modified period views with maintainer-period relationships."""

    def test_period_list_shows_only_maintainer_periods(self, client, maintainer_with_permissions, maintainer):
        """Test that period list shows only periods assigned to current maintainer."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)

        # Create periods
        assigned_period = Period.objects.create(name="Assigned Period")
        unassigned_period = Period.objects.create(name="Unassigned Period")

        # Assign only one period to maintainer
        MaintainerPeriod.objects.create(maintainer=maintainer, period=assigned_period)

        url = reverse("maintainer:period_list")
        response = client.get(url)

        assert response.status_code == 200
        assert "Assigned Period" in response.content.decode()
        assert "Unassigned Period" not in response.content.decode()

    def test_period_create_assigns_to_maintainer(self, client, maintainer_with_permissions, maintainer):
        """Test that creating period automatically assigns it to current maintainer."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:period_create")
        data = {"name": "Auto Assigned Period", "description": "This should be auto-assigned"}

        response = client.post(url, data=data)

        assert response.status_code == 302  # Redirect after successful creation

        # Verify period was created and assigned
        period = Period.objects.get(name="Auto Assigned Period")
        assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_period_delete_removes_maintainer_relationship(
        self, client, maintainer_with_permissions, maintainer, collection
    ):
        """Test that period delete removes maintainer-period relationship."""
        from adoration.models import MaintainerPeriod, Period, PeriodCollection

        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create period and assign to maintainer
        period = Period.objects.create(name="Test Relationship Period")
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)
        PeriodCollection.objects.create(collection=collection, period=period)

        url = reverse("maintainer:period_delete", kwargs={"pk": period.pk})
        response = client.post(url)

        assert response.status_code == 302  # Redirect after successful removal

        # Period should still exist, but maintainer relationship should be removed
        assert Period.objects.filter(id=period.id).exists()
        assert not MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()
        assert not PeriodCollection.objects.filter(collection=collection, period=period).exists()

    def test_collection_detail_shows_only_maintainer_periods(
        self, client, maintainer_with_permissions, maintainer, collection
    ):
        """Test that collection detail shows only periods assigned to current maintainer."""
        from adoration.models import MaintainerPeriod, Period, PeriodCollection

        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create periods
        maintainer_period = Period.objects.create(name="Maintainer Period")
        other_period = Period.objects.create(name="Other Period")

        # Assign only one period to maintainer
        MaintainerPeriod.objects.create(maintainer=maintainer, period=maintainer_period)

        # Assign both periods to collection
        PeriodCollection.objects.create(collection=collection, period=maintainer_period)
        PeriodCollection.objects.create(collection=collection, period=other_period)

        url = reverse("maintainer:collection_detail", kwargs={"pk": collection.pk})
        response = client.get(url)

        assert response.status_code == 200
        # Should only show the maintainer's period
        context = response.context
        period_collections = context["period_collections"]
        assert len(period_collections) == 1
        assert period_collections[0].period == maintainer_period

    def test_assign_period_with_maintainer_period_check(
        self, client, maintainer_with_permissions, maintainer, collection
    ):
        """Test period assignment requires maintainer-period relationship."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Create period but don't assign to maintainer
        period = Period.objects.create(name="Unassigned Period")

        url = reverse("maintainer:assign_period")
        data = {"collection_id": collection.id, "period_id": period.id}

        response = client.post(url, data=data)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

        # Should create maintainer-period relationship automatically
        assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()


@pytest.mark.django_db
class TestAssignStandardPeriods:
    """Test cases for assign_standard_periods_to_maintainer AJAX view."""

    def test_assign_standard_periods_success(self, client, maintainer_with_permissions, maintainer):
        """Test successful assignment of standard periods to maintainer."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "assigned" in json_data["message"].lower()

        # Verify all 24 periods were created and assigned
        from adoration.models import MaintainerPeriod, Period

        # Check that 24 standard periods exist
        standard_periods = []
        for hour in range(0, 24):
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"
            period = Period.objects.get(name=period_name)
            standard_periods.append(period)

        assert len(standard_periods) == 24

        # Check that all are assigned to the maintainer
        for period in standard_periods:
            assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

        # Verify the counts in response
        assert json_data["created_count"] == 24
        assert json_data["assigned_count"] == 24

    def test_assign_standard_periods_already_exist(self, client, maintainer_with_permissions, maintainer):
        """Test assignment when some periods already exist."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)

        # Pre-create some periods
        existing_periods = []
        for hour in range(0, 5):  # Create first 5 hours
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"
            period = Period.objects.create(name=period_name, description=f"Existing period {hour}")
            existing_periods.append(period)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

        # Should have created 19 new periods (24 - 5 existing)
        assert json_data["created_count"] == 19
        # Should have assigned all 24 periods
        assert json_data["assigned_count"] == 24

        # Verify all periods exist and are assigned
        for hour in range(0, 24):
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"
            period = Period.objects.get(name=period_name)
            assert MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists()

    def test_assign_standard_periods_already_assigned(self, client, maintainer_with_permissions, maintainer):
        """Test assignment when periods already exist and are assigned."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)

        # Pre-create and assign some periods
        for hour in range(0, 10):  # Create and assign first 10 hours
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"
            period = Period.objects.create(name=period_name, description=f"Pre-assigned period {hour}")
            MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

        # Should have created 14 new periods (24 - 10 existing)
        assert json_data["created_count"] == 14
        # Should have assigned 14 new periods (24 - 10 already assigned)
        assert json_data["assigned_count"] == 14

    def test_assign_standard_periods_all_already_assigned(self, client, maintainer_with_permissions, maintainer):
        """Test assignment when all periods already exist and are assigned."""
        from adoration.models import MaintainerPeriod, Period

        client.force_login(maintainer_with_permissions)

        # Pre-create and assign all 24 periods
        for hour in range(0, 24):
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"
            period = Period.objects.create(name=period_name, description=f"Pre-assigned period {hour}")
            MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert "already assigned" in json_data["message"]

        # Should not have created or assigned any new periods
        assert json_data["created_count"] == 0
        assert json_data["assigned_count"] == 0

    def test_assign_standard_periods_invalid_method(self, client, maintainer_with_permissions):
        """Test assignment with invalid HTTP method."""
        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_standard_periods")
        response = client.get(url)  # Should be POST

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "invalid method" in json_data["error"].lower()

    def test_assign_standard_periods_non_maintainer(self, client, django_user_model):
        """Test assignment by non-maintainer returns error."""
        user = django_user_model.objects.create_user(
            username="regular_user", email="user@example.com", password="testpass123"
        )
        client.force_login(user)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "not a maintainer" in json_data["error"]

    def test_assign_standard_periods_creates_correct_names(self, client, maintainer_with_permissions, maintainer):
        """Test that standard periods are created with correct names and descriptions."""
        from adoration.models import Period

        client.force_login(maintainer_with_permissions)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True

        # Verify specific period names and descriptions
        test_cases = [
            ("00:00 - 01:00", "Adoration period from 00:00 to 01:00"),
            ("01:00 - 02:00", "Adoration period from 01:00 to 02:00"),
            ("12:00 - 13:00", "Adoration period from 12:00 to 13:00"),
            ("23:00 - 00:00", "Adoration period from 23:00 to 00:00"),
        ]

        for period_name, expected_description in test_cases:
            period = Period.objects.get(name=period_name)
            assert period.description == expected_description

    def test_assign_standard_periods_error_handling(self, client, maintainer_with_permissions, maintainer, monkeypatch):
        """Test error handling when period creation fails."""
        client.force_login(maintainer_with_permissions)

        # Mock Period.objects.get_or_create to raise an exception
        def mock_get_or_create(*args, **kwargs):
            raise Exception("Database error")

        from adoration.models import Period

        monkeypatch.setattr(Period.objects, "get_or_create", mock_get_or_create)

        url = reverse("maintainer:assign_standard_periods")
        response = client.post(url)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is False
        assert "database error" in json_data["error"].lower()
