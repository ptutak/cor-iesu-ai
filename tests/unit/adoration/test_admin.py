"""
Unit tests for adoration admin.

This module contains comprehensive tests for all admin configurations
and custom methods in the adoration app.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory

from adoration.admin import (
    CollectionMaintainerAdmin,
    MaintainerAdmin,
    PeriodAdmin,
    PeriodAssignmentAdmin,
    PeriodCollectionAdmin,
)
from adoration.models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


class TestPeriodAdmin:
    """Test cases for PeriodAdmin."""

    def test_list_display(self, db):
        """Test that list_display shows correct fields."""
        admin = PeriodAdmin(Period, AdminSite())
        assert "name" in admin.list_display
        assert "description" in admin.list_display

    def test_search_fields(self, db):
        """Test that search fields are configured correctly."""
        admin = PeriodAdmin(Period, AdminSite())
        assert "name" in admin.search_fields
        assert "description" in admin.search_fields

    def test_list_filter(self, db):
        """Test that list filter is configured correctly."""
        admin = PeriodAdmin(Period, AdminSite())
        assert "name" in admin.list_filter


class TestPeriodCollectionAdmin:
    """Test cases for PeriodCollectionAdmin."""

    def test_list_display(self, db):
        """Test that list_display shows correct fields."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())
        assert "collection" in admin.list_display
        assert "period" in admin.list_display
        assert "get_assignment_count" in admin.list_display

    def test_get_assignment_count_with_assignments(self, db, period_collection):
        """Test get_assignment_count method with assignments."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())

        # Create some assignments
        for i in range(3):
            PeriodAssignment.create_with_email(email=f"test{i}@example.com", period_collection=period_collection).save()

        result = admin.get_assignment_count(period_collection)
        assert "3" in str(result)
        assert '<span style="font-weight: bold;">3</span>' in str(result)

    def test_get_assignment_count_no_assignments(self, db, period_collection):
        """Test get_assignment_count method without assignments."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())

        result = admin.get_assignment_count(period_collection)
        assert "0" in str(result)
        assert '<span style="font-weight: bold;">0</span>' in str(result)

    def test_get_assignment_count_short_description(self, db):
        """Test that get_assignment_count has correct short_description."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())
        assert hasattr(admin.get_assignment_count, "short_description")
        assert admin.get_assignment_count.short_description == "Assignments"

    def test_list_filter(self, db):
        """Test that list filter is configured correctly."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())
        assert "collection" in admin.list_filter

    def test_search_fields(self, db):
        """Test that search fields are configured correctly."""
        admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())
        assert "collection__name" in admin.search_fields
        assert "period__name" in admin.search_fields


class TestMaintainerAdmin:
    """Test cases for MaintainerAdmin."""

    def test_list_display(self, db):
        """Test that list_display shows correct fields."""
        admin = MaintainerAdmin(Maintainer, AdminSite())
        assert "get_full_name" in admin.list_display
        assert "user_email" in admin.list_display
        assert "phone_number" in admin.list_display
        assert "country" in admin.list_display

    def test_get_full_name_with_name(self, db, maintainer):
        """Test get_full_name method with full name."""
        admin = MaintainerAdmin(Maintainer, AdminSite())

        # Set full name
        maintainer.user.first_name = "John"
        maintainer.user.last_name = "Doe"
        maintainer.user.save()

        result = admin.get_full_name(maintainer)
        assert result == "John Doe"

    def test_get_full_name_without_name(self, db, maintainer_user):
        """Test get_full_name method without full name."""
        admin = MaintainerAdmin(Maintainer, AdminSite())

        # Clear the first and last name
        maintainer_user.first_name = ""
        maintainer_user.last_name = ""
        maintainer_user.save()

        maintainer = Maintainer.objects.create(user=maintainer_user, country="Test Country")

        result = admin.get_full_name(maintainer)
        assert result == maintainer_user.username

    def test_get_full_name_short_description(self, db):
        """Test that get_full_name has correct short_description."""
        admin = MaintainerAdmin(Maintainer, AdminSite())
        assert hasattr(admin.get_full_name, "short_description")
        assert admin.get_full_name.short_description == "Name"

    def test_user_email_method(self, db, maintainer):
        """Test user_email method."""
        admin = MaintainerAdmin(Maintainer, AdminSite())

        result = admin.user_email(maintainer)
        assert result == maintainer.user.email

    def test_user_email_short_description(self, db):
        """Test that user_email has correct short_description."""
        admin = MaintainerAdmin(Maintainer, AdminSite())
        assert hasattr(admin.user_email, "short_description")
        assert admin.user_email.short_description == "Email"

    def test_search_fields(self, db):
        """Test that search fields are configured correctly."""
        admin = MaintainerAdmin(Maintainer, AdminSite())
        expected_fields = [
            "user__first_name",
            "user__last_name",
            "user__username",
            "user__email",
            "phone_number",
            "country",
        ]
        for field in expected_fields:
            assert field in admin.search_fields

    def test_list_filter(self, db):
        """Test that list filter is configured correctly."""
        admin = MaintainerAdmin(Maintainer, AdminSite())
        assert "country" in admin.list_filter


class TestCollectionMaintainerAdmin:
    """Test cases for CollectionMaintainerAdmin."""

    def test_list_display(self, db):
        """Test that list_display shows correct fields."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        assert "collection" in admin.list_display
        assert "get_maintainer_name" in admin.list_display
        assert "get_maintainer_email" in admin.list_display
        assert "get_maintainer_country" in admin.list_display

    def test_get_maintainer_name_with_full_name(self, db, collection_maintainer):
        """Test get_maintainer_name method with full name."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())

        # Set full name
        collection_maintainer.maintainer.user.first_name = "Jane"
        collection_maintainer.maintainer.user.last_name = "Smith"
        collection_maintainer.maintainer.user.save()

        result = admin.get_maintainer_name(collection_maintainer)
        assert result == "Jane Smith"

    def test_get_maintainer_name_without_full_name(self, db, collection_maintainer):
        """Test get_maintainer_name method without full name."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())

        # Clear the first and last name
        collection_maintainer.maintainer.user.first_name = ""
        collection_maintainer.maintainer.user.last_name = ""
        collection_maintainer.maintainer.user.save()

        result = admin.get_maintainer_name(collection_maintainer)
        assert result == collection_maintainer.maintainer.user.username

    def test_get_maintainer_name_short_description(self, db):
        """Test that get_maintainer_name has correct short_description."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        assert hasattr(admin.get_maintainer_name, "short_description")
        assert admin.get_maintainer_name.short_description == "Maintainer Name"

    def test_get_maintainer_email(self, db, collection_maintainer):
        """Test get_maintainer_email method."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())

        result = admin.get_maintainer_email(collection_maintainer)
        assert result == collection_maintainer.maintainer.user.email

    def test_get_maintainer_email_short_description(self, db):
        """Test that get_maintainer_email has correct short_description."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        assert hasattr(admin.get_maintainer_email, "short_description")
        assert admin.get_maintainer_email.short_description == "Email"

    def test_get_maintainer_country(self, db, collection_maintainer):
        """Test get_maintainer_country method."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())

        result = admin.get_maintainer_country(collection_maintainer)
        assert result == collection_maintainer.maintainer.country

    def test_get_maintainer_country_short_description(self, db):
        """Test that get_maintainer_country has correct short_description."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        assert hasattr(admin.get_maintainer_country, "short_description")
        assert admin.get_maintainer_country.short_description == "Country"

    def test_search_fields(self, db):
        """Test that search fields are configured correctly."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        expected_fields = [
            "collection__name",
            "maintainer__user__first_name",
            "maintainer__user__last_name",
            "maintainer__user__username",
            "maintainer__user__email",
            "maintainer__country",
        ]
        for field in expected_fields:
            assert field in admin.search_fields

    def test_list_filter(self, db):
        """Test that list filter is configured correctly."""
        admin = CollectionMaintainerAdmin(CollectionMaintainer, AdminSite())
        assert "collection" in admin.list_filter
        assert "maintainer__country" in admin.list_filter


class TestPeriodAssignmentAdmin:
    """Test cases for PeriodAssignmentAdmin."""

    def test_list_display(self, db):
        """Test that list_display shows correct fields."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        assert "period_collection" in admin.list_display
        assert "get_email_status" in admin.list_display
        assert "deletion_token_short" in admin.list_display

    def test_get_email_status(self, db, period_assignment):
        """Test get_email_status method."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())

        result = admin.get_email_status(period_assignment)
        assert result == "Hashed for Privacy"

    def test_get_email_status_short_description(self, db):
        """Test that get_email_status has correct short_description."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        assert hasattr(admin.get_email_status, "short_description")
        assert admin.get_email_status.short_description == "Email Status"

    def test_deletion_token_short(self, db, period_assignment):
        """Test deletion_token_short method."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())

        result = admin.deletion_token_short(period_assignment)
        expected = f"{period_assignment.deletion_token[:8]}..."
        assert result == expected

    def test_deletion_token_short_empty_token(self, db, period_collection):
        """Test deletion_token_short method with empty token."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())

        # Create assignment without token
        assignment = PeriodAssignment(period_collection=period_collection)

        result = admin.deletion_token_short(assignment)
        assert result == ""

    def test_deletion_token_short_short_description(self, db):
        """Test that deletion_token_short has correct short_description."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        assert hasattr(admin.deletion_token_short, "short_description")
        assert admin.deletion_token_short.short_description == "Token"

    def test_readonly_fields(self, db):
        """Test that readonly_fields are configured correctly."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        assert "email_hash" in admin.readonly_fields
        assert "salt" in admin.readonly_fields
        assert "deletion_token" in admin.readonly_fields

    def test_list_filter(self, db):
        """Test that list filter is configured correctly."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        assert "period_collection__collection" in admin.list_filter
        assert "period_collection__period" in admin.list_filter

    def test_search_fields(self, db):
        """Test that search fields are configured correctly."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        expected_fields = [
            "period_collection__collection__name",
            "period_collection__period__name",
            "deletion_token",
        ]
        for field in expected_fields:
            assert field in admin.search_fields

    def test_has_change_permission_denied(self, db):
        """Test that change permission is denied for privacy."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        request = RequestFactory().get("/")

        assert admin.has_change_permission(request) is False
        assert admin.has_change_permission(request, obj=None) is False

    def test_has_add_permission_denied(self, db):
        """Test that add permission is denied for privacy."""
        admin = PeriodAssignmentAdmin(PeriodAssignment, AdminSite())
        request = RequestFactory().get("/")

        assert admin.has_add_permission(request) is False


class TestAdminDisplayDecorator:
    """Test cases for admin_display decorator."""

    def test_admin_display_decorator_sets_description(self, db):
        """Test that admin_display decorator sets short_description."""
        from adoration.admin import admin_display

        @admin_display("Test Description")
        def test_method(obj):
            return "test"

        assert hasattr(test_method, "short_description")
        assert test_method.short_description == "Test Description"

    def test_admin_display_decorator_preserves_function(self, db):
        """Test that admin_display decorator preserves function behavior."""
        from adoration.admin import admin_display

        @admin_display("Test Description")
        def test_method(obj):
            return f"result: {obj}"

        result = test_method("input")
        assert result == "result: input"
        assert test_method.short_description == "Test Description"


class TestAdminIntegration:
    """Integration tests for admin functionality."""

    def test_all_admins_registered(self, db):
        """Test that all expected admin classes are registered."""
        from django.contrib import admin

        from adoration import models

        # Check that key models have admin registered
        assert models.Period in admin.site._registry
        assert models.Collection in admin.site._registry
        assert models.Config in admin.site._registry
        assert models.CollectionConfig in admin.site._registry
        assert models.Maintainer in admin.site._registry
        assert models.CollectionMaintainer in admin.site._registry
        assert models.PeriodAssignment in admin.site._registry
        assert models.PeriodCollection in admin.site._registry

    def test_admin_methods_with_real_data(self, db, complete_setup):
        """Test admin methods with real data from fixtures."""
        setup = complete_setup

        # Test PeriodCollectionAdmin with real data
        pc_admin = PeriodCollectionAdmin(PeriodCollection, AdminSite())
        count_result = pc_admin.get_assignment_count(setup["period_collection"])
        assert "0" in str(count_result)  # No assignments yet

        # Add assignment and test again
        PeriodAssignment.create_with_email(
            email="admin_test@example.com", period_collection=setup["period_collection"]
        ).save()

        count_result = pc_admin.get_assignment_count(setup["period_collection"])
        assert "1" in str(count_result)

        # Test MaintainerAdmin with real data
        m_admin = MaintainerAdmin(Maintainer, AdminSite())
        name_result = m_admin.get_full_name(setup["maintainer"])
        email_result = m_admin.user_email(setup["maintainer"])

        assert name_result != ""
        assert "@" in email_result
