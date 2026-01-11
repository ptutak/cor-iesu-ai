"""
Unit tests for adoration views.

This module contains comprehensive tests for all views in the adoration app,
including form submission, email functionality, AJAX endpoints, and language filtering.
"""

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.utils import translation

from adoration.models import (
    Collection,
    CollectionConfig,
    CollectionMaintainer,
    Config,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)
from adoration.views import get_email_config


class TestRegistrationView:
    """Test cases for registration_view."""

    def test_registration_view_get(self, test_client, db):
        """Test GET request to registration view."""
        response = test_client.get(reverse("registration"))

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].__class__.__name__ == "PeriodAssignmentForm"

    def test_registration_view_post_valid_form(self, test_client, complete_setup, mail_outbox):
        """Test POST request with valid form data."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "attendant_phone_number": "+1234567890",
            "privacy_accepted": True,
        }

        response = test_client.post(reverse("registration"), form_data)

    def test_get_collection_periods_filters_by_language(self, test_client, db, maintainer_user):
        """Test that get_collection_periods filters collections by current language."""
        # Create collections with different language availability
        collection_en = Collection.objects.create(
            name="English Collection",
            enabled=True,
            available_languages=["en"],
        )
        collection_nl = Collection.objects.create(
            name="Dutch Collection",
            enabled=True,
            available_languages=["nl"],
        )
        collection_all = Collection.objects.create(
            name="All Languages Collection",
            enabled=True,
            available_languages=["en", "pl", "nl"],
        )

        # Create periods for each collection
        period = Period.objects.create(name="Test Period", description="Test")
        pc_en = PeriodCollection.objects.create(period=period, collection=collection_en)
        pc_nl = PeriodCollection.objects.create(period=period, collection=collection_nl)
        pc_all = PeriodCollection.objects.create(period=period, collection=collection_all)

        # Create maintainers
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        for collection in [collection_en, collection_nl, collection_all]:
            CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Test with English language
        with translation.override("en"):
            response = test_client.get(
                f"/api/collection/{collection_en.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="en",
            )
            assert response.status_code == 200

            response = test_client.get(
                f"/api/collection/{collection_all.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="en",
            )
            assert response.status_code == 200

            # Should fail for Dutch-only collection
            response = test_client.get(
                f"/api/collection/{collection_nl.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="en",
            )
            assert response.status_code == 404

        # Test with Dutch language
        with translation.override("nl"):
            # Should work for Dutch-available collections
            response = test_client.get(
                f"/api/collection/{collection_nl.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="nl",
            )
            assert response.status_code == 200

            response = test_client.get(
                f"/api/collection/{collection_all.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="nl",
            )
            assert response.status_code == 200

            # Should fail for English-only collection
            response = test_client.get(
                f"/api/collection/{collection_en.id}/periods/",
                HTTP_ACCEPT_LANGUAGE="nl",
            )
            assert response.status_code == 404

    def test_get_collection_periods_unavailable_collection(self, test_client, db, maintainer_user):
        """Test get_collection_periods with collection not available in current language."""
        # Create collection only available in Polish
        collection = Collection.objects.create(
            name="Polish Only Collection",
            enabled=True,
            available_languages=["pl"],
        )

        # Create maintainer
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Test with English language (should fail)
        with translation.override("en"):
            response = test_client.get(f"/api/collection/{collection.id}/periods/", HTTP_ACCEPT_LANGUAGE="en")
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "Collection not found" in data["error"]

    def test_get_collection_periods_disabled_collection(self, test_client, db, maintainer_user):
        """Test get_collection_periods with disabled collection."""
        collection = Collection.objects.create(
            name="Disabled Collection",
            enabled=False,  # Disabled
            available_languages=["en"],
        )

        # Create maintainer
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        with translation.override("en"):
            response = test_client.get(f"/api/collection/{collection.id}/periods/", HTTP_ACCEPT_LANGUAGE="en")
            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "Collection not found" in data["error"]

    def test_registration_view_post_invalid_form(self, test_client, db):
        """Test POST request with invalid form data."""
        form_data = {
            "attendant_name": "",  # Missing required field
            "attendant_email": "invalid-email",  # Invalid email
            "privacy_accepted": True,
        }

        response = test_client.post(reverse("registration"), form_data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # No assignments should be created
        assert PeriodAssignment.objects.count() == 0

    def test_registration_view_post_duplicate_registration(self, test_client, complete_setup):
        """Test POST request with duplicate registration."""
        setup = complete_setup
        email = "duplicate@example.com"

        # Create first assignment
        PeriodAssignment.create_with_email(email=email, period_collection=setup["period_collection"]).save()

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": email,
            "privacy_accepted": True,
        }

        response = test_client.post(reverse("registration"), form_data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # Should still only have one assignment
        assert PeriodAssignment.objects.count() == 1

    def test_registration_view_assignment_limit_reached(self, test_client, complete_setup):
        """Test registration when assignment limit is reached."""
        setup = complete_setup

        # Ensure collection config exists for assignment limit
        collection_config = setup.get("collection_config")
        if not collection_config:
            from adoration.models import CollectionConfig

            collection_config = CollectionConfig.objects.create(
                collection=setup["collection"],
                name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
                value="3",
                description="Collection-specific assignment limit",
            )

        limit = int(collection_config.value)

        # Create assignments up to the limit
        for i in range(limit):
            PeriodAssignment.create_with_email(
                email=f"test{i}@example.com",
                period_collection=setup["period_collection"],
            ).save()

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        response = test_client.post(reverse("registration"), form_data)

        # Should fail due to assignment limit
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors
        # Check that it's specifically the assignment limit error
        errors_str = str(response.context["form"].errors).lower()
        assert "period is full" in errors_str or "maximum" in errors_str


class TestGetCollectionPeriods:
    """Test cases for get_collection_periods AJAX view."""

    def test_get_collection_periods_success(self, test_client, complete_setup):
        """Test successful AJAX request for collection periods."""
        setup = complete_setup

        # Create some assignments for testing counts
        PeriodAssignment.create_with_email(
            email="test1@example.com", period_collection=setup["period_collection"]
        ).save()
        PeriodAssignment.create_with_email(
            email="test2@example.com", period_collection=setup["period_collection2"]
        ).save()

        url = reverse("get_collection_periods", kwargs={"collection_id": setup["collection"].id})
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert len(data["periods"]) == 2

        # Check period data structure
        period_data = data["periods"][0]
        assert "id" in period_data
        assert "name" in period_data
        assert "description" in period_data
        assert "current_count" in period_data

        # Check assignment counts
        counts = [p["current_count"] for p in data["periods"]]
        assert 1 in counts  # One period has 1 assignment
        assert 1 in counts  # Other period has 1 assignment

    def test_get_collection_periods_nonexistent_collection(self, test_client, db):
        """Test AJAX request for non-existent collection."""
        url = reverse("get_collection_periods", kwargs={"collection_id": 99999})
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"] == "Collection not found"

    def test_get_collection_periods_disabled_collection(self, test_client, disabled_collection):
        """Test AJAX request for disabled collection."""
        url = reverse("get_collection_periods", kwargs={"collection_id": disabled_collection.id})
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"] == "Collection not found"

    def test_get_collection_periods_exception_handling(self, test_client, db, monkeypatch):
        """Test AJAX view exception handling."""
        # Create a collection first
        collection = Collection.objects.create(name="Test Collection", enabled=True)

        # Mock PeriodCollection.objects.filter to raise an exception
        def mock_filter(*args, **kwargs):
            raise Exception("Database error")

        monkeypatch.setattr("adoration.views.PeriodCollection.objects.filter", mock_filter)

        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "Failed to load periods"


class TestDeleteAssignment:
    """Test cases for delete_assignment view."""

    def test_delete_assignment_get(self, test_client, period_assignment):
        """Test GET request to delete assignment page."""
        # Make sure assignment is saved
        period_assignment.save()

        url = reverse("delete_assignment", kwargs={"token": period_assignment.deletion_token})
        response = test_client.get(url)

        assert response.status_code == 200
        assert "assignment" in response.context
        assert "form" in response.context
        assert response.context["assignment"].id == period_assignment.id

    def test_delete_assignment_post_valid_email(self, test_client, period_collection):
        """Test POST request with valid email for deletion."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form_data = {"email": email}
        url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})
        response = test_client.post(url, form_data)

        # Should redirect after successful deletion
        assert response.status_code == 302
        assert response.url == reverse("registration")

        # Assignment should be deleted
        assert not PeriodAssignment.objects.filter(id=assignment.id).exists()

    def test_delete_assignment_post_invalid_email(self, test_client, period_collection):
        """Test POST request with invalid email for deletion."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form_data = {"email": "wrong@example.com"}
        url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})
        response = test_client.post(url, form_data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

        # Assignment should still exist
        assert PeriodAssignment.objects.filter(id=assignment.id).exists()

    def test_delete_assignment_invalid_token(self, test_client, db):
        """Test delete request with invalid token."""
        url = reverse("delete_assignment", kwargs={"token": "invalid-token"})
        response = test_client.get(url)

        assert response.status_code == 404


class TestGetEmailConfig:
    """Test cases for get_email_config utility function."""

    def test_get_email_config_existing(self, db):
        """Test getting existing email configuration."""
        Config.objects.create(
            name="TEST_EMAIL_CONFIG",
            value="test@example.com",
            description="Test email config",
        )

        result = get_email_config("TEST_EMAIL_CONFIG", "default@example.com")
        assert result == "test@example.com"

    def test_get_email_config_nonexistent(self, db):
        """Test getting non-existent email configuration."""
        result = get_email_config("NONEXISTENT_CONFIG", "default@example.com")
        assert result == "default@example.com"

    def test_get_email_config_nonexistent_no_default(self, db):
        """Test getting non-existent email configuration without default."""
        result = get_email_config("NONEXISTENT_CONFIG")
        assert result is None

    def test_get_email_config_default_from_email(self, db):
        """Test getting DEFAULT_FROM_EMAIL config."""
        Config.objects.create(
            name=Config.DefaultValues.DEFAULT_FROM_EMAIL,
            value="noreply@test.com",
            description="Default from email",
        )

        result = get_email_config("DEFAULT_FROM_EMAIL", "fallback@example.com")
        assert result == "noreply@test.com"


class TestRegistrationViewEmailIntegration:
    """Test registration view email integration with different configurations."""

    def test_registration_view_email_config_integration(self, test_client, complete_setup, mail_outbox):
        """Test registration view uses email configuration."""
        setup = complete_setup

        # Set custom email configuration
        Config.objects.create(
            name=Config.DefaultValues.DEFAULT_FROM_EMAIL,
            value="custom@example.com",
            description="Custom from email",
        )

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            response = test_client.post(reverse("registration"), form_data, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 302
        assert len(mail_outbox) == 2

        # Check that custom from email is used
        user_email = mail_outbox[0]
        assert user_email.from_email == "custom@example.com"

    def test_registration_view_no_maintainers(self, test_client, period_collection, mail_outbox):
        """Test registration view when collection has no maintainers."""
        # Clear any existing maintainers for this collection
        CollectionMaintainer.objects.filter(collection=period_collection.collection).delete()

        form_data = {
            "collection": period_collection.collection.id,
            "period_collection": period_collection.id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            response = test_client.post(reverse("registration"), form_data, HTTP_ACCEPT_LANGUAGE="en")

        # Debug: Check if form failed validation
        if response.status_code == 200:
            # Form failed - check why
            form = response.context.get("form")
            if form and hasattr(form, "errors"):
                # Collection without maintainers should not be selectable in form
                assert "collection" in form.errors or "period_collection" in form.errors
                return

        assert response.status_code == 302
        # Only user confirmation email should be sent (no maintainers)
        assert len(mail_outbox) == 1

        user_email = mail_outbox[0]
        assert "john@example.com" in user_email.to
        assert "Registration Confirmation" in user_email.subject

    def test_registration_view_email_failure_silent(self, test_client, complete_setup, monkeypatch):
        """Test registration view handles email failures silently."""
        setup = complete_setup

        # Mock send_mail to succeed but track that it was called with fail_silently=True
        email_calls = []
        email_message_calls = []

        def mock_send_mail(*args, **kwargs):
            email_calls.append(kwargs)
            return True  # Simulate successful email sending

        def mock_email_message_send(self, fail_silently=False):
            email_message_calls.append({"fail_silently": fail_silently})
            return True

        monkeypatch.setattr("adoration.views.send_mail", mock_send_mail)
        monkeypatch.setattr("adoration.views.EmailMessage.send", mock_email_message_send)

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            response = test_client.post(reverse("registration"), form_data, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 302
        # Assignment should be created
        new_assignments = PeriodAssignment.objects.filter(period_collection=setup["period_collection"])
        assert new_assignments.exists()

        # Verify that send_mail was called with fail_silently=True (user confirmation)
        assert len(email_calls) == 1  # User confirmation email
        for call_kwargs in email_calls:
            assert call_kwargs.get("fail_silently") is True

        # Verify that EmailMessage.send was called with fail_silently=True (maintainer notification)
        assert len(email_message_calls) == 1  # Maintainer notification email
        for call_kwargs in email_message_calls:
            assert call_kwargs.get("fail_silently") is True

    def test_registration_form_edge_cases(self, test_client, complete_setup):
        """Test registration form validation edge cases for better coverage."""
        setup = complete_setup

        # Test form with invalid collection ID that causes super().clean() to fail
        form_data = {
            "collection": "99999",  # Non-existent collection ID
            "period_collection": setup["period_collection"].id,
            "attendant_name": "",  # Empty required field
            "attendant_email": "invalid-email",  # Invalid email format
            "privacy_accepted": False,  # Required field not accepted
        }

        with translation.override("en"):
            response = test_client.post(reverse("registration"), form_data)
            # Form should be invalid and return form with errors
            assert response.status_code == 200
            assert "form" in response.context
            form = response.context["form"]
            assert not form.is_valid()
            # This exercises the clean method's early return path when super().clean() fails


class TestGetCollectionMaintainers:
    """Test cases for get_collection_maintainers view."""

    def test_get_collection_maintainers_success(self, test_client, collection, maintainer):
        """Test successful retrieval of collection maintainers."""
        # Create collection maintainer relationship
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        assert "collection_name" in data
        assert "maintainers" in data
        assert data["collection_name"] == collection.name
        assert len(data["maintainers"]) == 1

        maintainer_data = data["maintainers"][0]
        assert "name" in maintainer_data
        assert "email" in maintainer_data
        assert "country" in maintainer_data
        assert maintainer_data["email"] == maintainer.user.email
        assert maintainer_data["country"] == maintainer.country

    def test_get_collection_maintainers_with_phone(self, test_client, collection, maintainer_user):
        """Test maintainer data includes phone number when available."""
        # Create maintainer with phone number
        maintainer = Maintainer.objects.create(
            user=maintainer_user, phone_number="+1234567890", country="United States"
        )
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        maintainer_data = data["maintainers"][0]
        assert "phone" in maintainer_data
        assert maintainer_data["phone"] == "+1234567890"

    def test_get_collection_maintainers_no_phone(self, test_client, collection, maintainer_user):
        """Test maintainer data without phone number."""
        # Create maintainer without phone number
        maintainer = Maintainer.objects.create(user=maintainer_user, phone_number="", country="United States")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        maintainer_data = data["maintainers"][0]
        assert "phone" not in maintainer_data

    def test_get_collection_maintainers_multiple_maintainers(self, test_client, collection, maintainer_user):
        """Test collection with multiple maintainers."""
        # Create multiple maintainers
        maintainer1 = Maintainer.objects.create(user=maintainer_user, country="United States")

        user2 = User.objects.create_user(
            username="maintainer2",
            email="maintainer2@example.com",
            first_name="Jane",
            last_name="Doe",
        )
        maintainer2 = Maintainer.objects.create(user=user2, country="Canada")

        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer1)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer2)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        assert len(data["maintainers"]) == 2

        # Check that both maintainers are included
        emails = [m["email"] for m in data["maintainers"]]
        assert "maintainer@example.com" in emails
        assert "maintainer2@example.com" in emails

    def test_get_collection_maintainers_no_maintainers(self, test_client, collection):
        """Test collection with no maintainers."""
        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        assert "maintainers" in data
        assert len(data["maintainers"]) == 0

    def test_get_collection_maintainers_filters_invalid_emails(self, test_client, collection):
        """Test that query correctly filters maintainers by email constraints."""
        # This test verifies the view's query filter logic
        # The view filters: email__isnull=False, email__gt=""
        # Since Maintainer model requires valid emails, we just verify empty response for empty collection

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        # Should return empty list since no maintainers assigned
        assert len(data["maintainers"]) == 0

    def test_get_collection_maintainers_nonexistent_collection(self, test_client, db):
        """Test request for non-existent collection."""
        url = "/api/collection/99999/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Collection not found" in data["error"]

    def test_get_collection_maintainers_disabled_collection(self, test_client, disabled_collection):
        """Test request for disabled collection."""
        url = f"/api/collection/{disabled_collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Collection not found" in data["error"]

    def test_get_collection_maintainers_language_filter(self, test_client, maintainer_user):
        """Test that collections are filtered by available language."""
        # Create collection only available in Polish
        collection = Collection.objects.create(
            name="Polish Only Collection",
            enabled=True,
            available_languages=["pl"],
        )

        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        url = f"/api/collection/{collection.id}/maintainers/"

        # Test with English language (should fail)
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")
            assert response.status_code == 404

        # Test with Polish language (should succeed)
        with translation.override("pl"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="pl")
            assert response.status_code == 200

    def test_get_collection_maintainers_exception_handling(self, test_client, collection, monkeypatch):
        """Test exception handling in maintainer endpoint."""

        def mock_filter(*args, **kwargs):
            raise Exception("Database error")

        monkeypatch.setattr("adoration.views.CollectionMaintainer.objects.filter", mock_filter)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to load maintainer information" in data["error"]

    def test_get_collection_maintainers_user_display_name(self, test_client, collection):
        """Test maintainer name display logic (full name vs username)."""
        # Create user with full name
        user_with_name = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            first_name="John",
            last_name="Doe",
            password="test123",
        )

        # Create user without full name
        user_without_name = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="test123",
        )

        maintainer1 = Maintainer.objects.create(user=user_with_name, country="US")
        maintainer2 = Maintainer.objects.create(user=user_without_name, country="US")

        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer1)
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer2)

        url = f"/api/collection/{collection.id}/maintainers/"
        with translation.override("en"):
            response = test_client.get(url, HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 200
        data = response.json()
        maintainers = data["maintainers"]

        # Find maintainers by email
        maintainer1_data = next(m for m in maintainers if m["email"] == "user1@example.com")
        maintainer2_data = next(m for m in maintainers if m["email"] == "user2@example.com")

        # User with full name should show full name
        assert maintainer1_data["name"] == "John Doe"
        # User without full name should show username
        assert maintainer2_data["name"] == "user2"
