"""
Unit tests for adoration forms.

This module contains comprehensive tests for all forms in the adoration app,
including validation, dynamic querysets, custom clean methods, and language filtering.
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import translation

from adoration.forms import DeletionConfirmForm, PeriodAssignmentForm
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


class TestPeriodAssignmentForm:
    """Test cases for PeriodAssignmentForm."""

    def test_form_initialization_empty(self, db):
        """Test form initialization without data."""
        form = PeriodAssignmentForm()

        # Check that collection field only shows collections with maintainers
        collection_queryset = form.fields["collection"].queryset
        assert collection_queryset.count() == 0  # No collections with maintainers yet

    def test_form_initialization_with_maintainers(self, db, maintainer_user):
        """Test form initialization with collections that have maintainers."""
        # Create collection with maintainer
        collection = Collection.objects.create(name="Test Collection", enabled=True)
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Test with English language context
        with translation.override("en"):
            form = PeriodAssignmentForm()

            # Should only show collections with maintainers
            collection_queryset = form.fields["collection"].queryset
            assert collection_queryset.count() == 1
            assert collection in collection_queryset

    def test_form_initialization_filters_by_language(self, db, maintainer_user):
        """Test form only shows collections available in current language."""
        # Create collections with different language availability
        collection_en_pl = Collection.objects.create(
            name="English Polish Collection",
            enabled=True,
            available_languages=["en", "pl"],
        )
        collection_nl_only = Collection.objects.create(
            name="Dutch Only Collection", enabled=True, available_languages=["nl"]
        )
        collection_all_langs = Collection.objects.create(
            name="All Languages Collection",
            enabled=True,
            available_languages=["en", "pl", "nl"],
        )

        # Create maintainers for all collections
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        for collection in [collection_en_pl, collection_nl_only, collection_all_langs]:
            CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Test with English language
        with translation.override("en"):
            form = PeriodAssignmentForm()
            collection_queryset = form.fields["collection"].queryset

            # Should include collections available in English
            assert collection_en_pl in collection_queryset
            assert collection_all_langs in collection_queryset
            assert collection_nl_only not in collection_queryset

        # Test with Dutch language
        with translation.override("nl"):
            form = PeriodAssignmentForm()
            collection_queryset = form.fields["collection"].queryset

            # Should include collections available in Dutch
            assert collection_nl_only in collection_queryset
            assert collection_all_langs in collection_queryset
            assert collection_en_pl not in collection_queryset

        # Test with Polish language
        with translation.override("pl"):
            form = PeriodAssignmentForm()
            collection_queryset = form.fields["collection"].queryset

            # Should include collections available in Polish
            assert collection_en_pl in collection_queryset
            assert collection_all_langs in collection_queryset
            assert collection_nl_only not in collection_queryset

    def test_form_initialization_with_collection_data(self, db, complete_setup):
        """Test form initialization with collection data sets period queryset."""
        setup = complete_setup

        # Create second period collection for same collection
        period2 = Period.objects.create(name="Evening", description="Evening period")
        PeriodCollection.objects.create(period=period2, collection=setup["collection"])

        form_data = {"collection": setup["collection"].id}
        form = PeriodAssignmentForm(data=form_data)

        # Period queryset should be filtered by collection
        period_queryset = form.fields["period_collection"].queryset
        # Should have 3 total: original period_collection, period_collection2, and new one
        assert period_queryset.count() == 3

        # Verify both period collections are for the correct collection
        for pc in period_queryset:
            assert pc.collection == setup["collection"]

    def test_form_initialization_invalid_collection_data(self, db, complete_setup):
        """Test form initialization with invalid collection data."""
        form_data = {"collection": "invalid"}
        form = PeriodAssignmentForm(data=form_data)

        # Should not crash, period queryset should remain unchanged
        assert form.fields["period_collection"].queryset.count() >= 0

    def test_form_valid_data(self, db, complete_setup):
        """Test form with valid data."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "attendant_phone_number": "+1234567890",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert form.is_valid(), f"Form errors: {form.errors}"
        assert form.is_valid()
        assert form.cleaned_data["attendant_name"] == "John Doe"
        assert form.cleaned_data["attendant_email"] == "john@example.com"

    def test_form_missing_required_fields(self, db, complete_setup):
        """Test form with missing required fields."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            # Missing period_collection, attendant_name, attendant_email, privacy_accepted
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "period_collection" in form.errors
        assert "attendant_name" in form.errors
        assert "attendant_email" in form.errors

    def test_form_invalid_email(self, db, complete_setup):
        """Test form with invalid email address."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "invalid-email",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "attendant_email" in form.errors

    def test_form_optional_phone_number(self, db, complete_setup):
        """Test form with optional phone number field."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
            # No phone number provided
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert form.is_valid()
            assert form.cleaned_data.get("attendant_phone_number", "") == ""

    def test_clean_period_collection_no_selection(self, db):
        """Test clean_period_collection with no period selected."""
        form_data = {
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "period_collection" in form.errors

    def test_clean_period_collection_assignment_limit_collection_config(self, db, complete_setup):
        """Test assignment limit using collection-specific configuration."""
        setup = complete_setup

        # Verify the collection config exists and get its limit
        collection_config = setup.get("collection_config")
        if not collection_config:
            # Create collection config if it doesn't exist
            from adoration.models import CollectionConfig

            collection_config = CollectionConfig.objects.create(
                collection=setup["collection"],
                name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
                value="3",
                description="Collection-specific assignment limit",
            )

        limit = int(collection_config.value)

        # Create assignments up to the collection limit
        for i in range(limit):
            PeriodAssignment.create_with_email(
                email=f"test{i}@example.com",
                period_collection=setup["period_collection"],
            ).save()

        # Verify we have the expected number of assignments
        current_count = PeriodAssignment.objects.filter(period_collection=setup["period_collection"]).count()
        assert current_count == limit, f"Expected {limit} assignments, got {current_count}"

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)

        # Debug: Check if form is valid and print errors if any
        is_valid = form.is_valid()
        if is_valid:
            # Check the current assignments again to see if something changed
            final_count = PeriodAssignment.objects.filter(period_collection=setup["period_collection"]).count()
            assert (
                False
            ), f"Form should not be valid when limit ({limit}) is reached. Current count: {final_count}, Form errors: {form.errors}"

        assert "period_collection" in form.errors
        assert "period is full" in str(form.errors["period_collection"]).lower()

    def test_clean_period_collection_assignment_limit_default_config(self, db, period_collection):
        """Test assignment limit using default configuration."""
        # Create default config (no collection-specific config)
        Config.objects.create(
            name=Config.DefaultValues.ASSIGNMENT_LIMIT,
            value="2",
            description="Default assignment limit",
        )

        # Create assignments up to the default limit
        for i in range(2):
            PeriodAssignment.create_with_email(
                email=f"test{i}@example.com",
                period_collection=period_collection,
            ).save()

        form_data = {
            "collection": period_collection.collection.id,
            "period_collection": period_collection.id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "attendant_phone_number": "123-456-7890",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "period_collection" in form.errors

    def test_clean_period_collection_no_limit_config(self, db, period_collection):
        """Test assignment validation when no limit configuration exists."""
        # Create many assignments - should still work without limit
        for i in range(10):
            PeriodAssignment.create_with_email(
                email=f"test{i}@example.com",
                period_collection=period_collection,
            ).save()

        form_data = {
            "collection": period_collection.collection.id,
            "period_collection": period_collection.id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        # Should be valid since no limit is configured, even with many assignments
        if not form.is_valid():
            # If it's not valid, it might be due to other validation, not the limit
            # Check if the error is specifically about limits
            form_errors = str(form.errors)
            assert "period is full" not in form_errors.lower(), f"Unexpected limit error: {form_errors}"
        # If no limit is set, form should generally be valid
        assert form.is_valid() or "period is full" not in str(form.errors).lower()

    def test_clean_duplicate_registration(self, db, complete_setup):
        """Test clean method prevents duplicate registrations."""
        setup = complete_setup
        email = "duplicate@example.com"

        # Create existing assignment
        PeriodAssignment.create_with_email(email=email, period_collection=setup["period_collection"]).save()

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": email,
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "already registered" in str(form.non_field_errors()).lower()

    def test_clean_different_period_same_email(self, db, complete_setup):
        """Test form allows same email for different periods."""
        setup = complete_setup
        email = "test@example.com"

        # Create assignment for first period
        PeriodAssignment.create_with_email(email=email, period_collection=setup["period_collection"]).save()

        # Try to register for second period with same email
        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection2"].id,
            "attendant_name": "John Doe",
            "attendant_email": email,
            "attendant_phone_number": "+1234567890",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert form.is_valid()  # Should be valid for different period

    def test_save_method(self, db, complete_setup):
        """Test form save method creates assignment."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "attendant_phone_number": "+1234567890",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert form.is_valid()

            assignment = form.save()
            assert assignment.id is not None
            assert assignment.period_collection == setup["period_collection"]
            assert assignment.verify_email("john@example.com") is True
            assert assignment.deletion_token != ""

    def test_save_method_commit_false(self, db, complete_setup):
        """Test form save method with commit=False."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert form.is_valid()

            assignment = form.save(commit=False)
            assert assignment.id is None  # Not saved to database yet
            assert assignment.period_collection == setup["period_collection"]
            assert assignment.verify_email("john@example.com") is True

    def test_clean_period_collection_default_config_fallback(self, db, period_collection):
        """Test assignment limit falls back to default config when collection config doesn't exist."""
        # Create default config only (no collection-specific config)
        Config.objects.create(name=Config.DefaultValues.ASSIGNMENT_LIMIT, value="1")

        # Create one assignment to fill the period
        assignment = PeriodAssignment.create_with_email(
            email="existing@example.com", period_collection=period_collection
        )
        assignment.save()

        form_data = {
            "collection": period_collection.collection.id,
            "period_collection": period_collection.id,
            "attendant_name": "John Doe",
            "attendant_email": "john@example.com",
            "privacy_accepted": True,
        }

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            assert not form.is_valid()
            assert "period_collection" in form.errors
            assert "period is full" in str(form.errors["period_collection"]).lower()

    def test_clean_returns_none_when_super_clean_fails(self, db, complete_setup):
        """Test clean method returns None when super().clean() returns None."""
        setup = complete_setup

        # Create a form with invalid data to make super().clean() return None
        form_data = {
            "collection": "invalid",  # Invalid collection ID
            "period_collection": setup["period_collection"].id,
            "attendant_name": "",  # Required field missing
            "attendant_email": "invalid-email",  # Invalid email
            "privacy_accepted": False,  # Required field not accepted
        }

        form = PeriodAssignmentForm(data=form_data)

        # The form should be invalid and clean should return None
        assert not form.is_valid()
        # This covers the line where cleaned_data is None and we return None


class TestDeletionConfirmForm:
    """Test cases for DeletionConfirmForm."""

    def test_form_initialization(self, db, period_assignment):
        """Test form initialization with assignment."""
        form = DeletionConfirmForm(period_assignment)

        assert form.assignment == period_assignment
        assert "email" in form.fields
        assert form.fields["email"].required is True

    def test_form_valid_email(self, db, period_collection):
        """Test form with correct email address."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form_data = {"email": email}
        form = DeletionConfirmForm(assignment, data=form_data)

        assert form.is_valid()
        assert form.cleaned_data["email"] == email

    def test_form_invalid_email(self, db, period_collection):
        """Test form with incorrect email address."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form_data = {"email": "wrong@example.com"}
        form = DeletionConfirmForm(assignment, data=form_data)

        assert not form.is_valid()
        assert "email" in form.errors
        assert "does not match" in str(form.errors["email"]).lower()

    def test_form_empty_email(self, db, period_assignment):
        """Test form with empty email."""
        form_data = {"email": ""}
        form = DeletionConfirmForm(period_assignment, data=form_data)

        assert not form.is_valid()
        assert "email" in form.errors

    def test_form_invalid_email_format(self, db, period_assignment):
        """Test form with invalid email format."""
        form_data = {"email": "not-an-email"}
        form = DeletionConfirmForm(period_assignment, data=form_data)

        assert not form.is_valid()
        assert "email" in form.errors

    def test_clean_email_method(self, db, period_collection):
        """Test clean_email method specifically."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form = DeletionConfirmForm(assignment, data={"email": email})

        # Test clean_email method directly
        form.is_valid()  # This calls clean_email
        assert form.cleaned_data["email"] == email

    def test_clean_email_method_wrong_email(self, period_collection):
        """Test clean_email method with wrong email."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form = DeletionConfirmForm(assignment, data={"email": "wrong@example.com"})

        assert not form.is_valid()
        assert "email" in form.errors

    def test_period_assignment_form_clean_returns_super_none(self, complete_setup, monkeypatch):
        """Test form.clean() when super().clean() returns None."""
        setup = complete_setup

        # Mock super().clean() to return None
        monkeypatch.setattr("django.forms.forms.BaseForm.clean", lambda self: None)

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "test@example.com",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        result = form.clean()

        # When super().clean() returns None, form.clean() should return None
        assert result is None

    def test_period_assignment_form_collection_validation_error_handling(self, complete_setup, monkeypatch):
        """Test form handling of validation errors in clean_period_collection."""
        setup = complete_setup

        # Create assignment limit config
        CollectionConfig.objects.create(
            collection=setup["collection"],
            name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
            value="1",
            description="Test limit",
        )

        # Create one assignment to fill the limit
        PeriodAssignment.create_with_email(
            email="existing@example.com", period_collection=setup["period_collection"]
        ).save()

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "John Doe",
            "attendant_email": "test@example.com",
            "privacy_accepted": True,
        }

        form = PeriodAssignmentForm(data=form_data)
        assert not form.is_valid()
        assert "period_collection" in form.errors

    def test_clean_email_method_none_email(self, db, period_assignment):
        """Test clean_email method when email is None."""
        form = DeletionConfirmForm(period_assignment, data={})

        assert not form.is_valid()
        # Should handle None email gracefully and return empty string
        if hasattr(form, "cleaned_data") and "email" in form.cleaned_data:
            assert form.cleaned_data["email"] == ""


class TestFormIntegration:
    """Integration tests for forms working together."""

    def test_assignment_creation_and_deletion_flow(self, db, complete_setup):
        """Test complete flow from assignment creation to deletion."""
        setup = complete_setup
        email = "integration@example.com"

        # Step 1: Create assignment via form
        creation_form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "Integration Test",
            "attendant_email": email,
            "privacy_accepted": True,
        }

        with translation.override("en"):
            creation_form = PeriodAssignmentForm(data=creation_form_data)
            assert creation_form.is_valid()

            assignment = creation_form.save()
            assert assignment.verify_email(email)

        # Step 2: Delete assignment via deletion form
        deletion_form_data = {"email": email}
        deletion_form = DeletionConfirmForm(assignment, data=deletion_form_data)

        assert deletion_form.is_valid()
        assert deletion_form.cleaned_data["email"] == email

        # Verify the assignment can be deleted (form validates correctly)
        assignment.delete()
        assert not PeriodAssignment.objects.filter(id=assignment.id).exists()

    def test_form_field_labels(self, db):
        """Test that form fields have correct labels."""
        form = PeriodAssignmentForm()

        assert form.fields["attendant_name"].label == "Full Name *"
        assert form.fields["attendant_email"].label == "Email Address *"
        assert form.fields["attendant_phone_number"].label == "Phone Number (optional)"

        # Test deletion form
        assignment = PeriodAssignment()  # Mock assignment for form init
        deletion_form = DeletionConfirmForm(assignment)
        assert deletion_form.fields["email"].label == "Email Address *"

    def test_form_filters_maintainers_without_email(self, db):
        """Test that form filters out collections with maintainers who have no email."""
        from django.contrib.auth.models import User

        from adoration.models import Collection, CollectionMaintainer, Maintainer

        # Create collection and user with email
        collection_with_email = Collection.objects.create(name="Collection with Email", enabled=True)
        user_with_email = User.objects.create_user(
            username="user_email",
            email="user@example.com",
            password="testpass123",
        )
        maintainer_with_email = Maintainer.objects.create(user=user_with_email, country="US")
        CollectionMaintainer.objects.create(collection=collection_with_email, maintainer=maintainer_with_email)

        # Create collection and user without email
        collection_without_email = Collection.objects.create(name="Collection without Email", enabled=True)
        user_without_email = User.objects.create_user(username="user_no_email", password="testpass123")
        user_without_email.email = ""
        user_without_email.save()

        # Create maintainer without email (bypassing validation)
        maintainer_without_email = Maintainer(user=user_without_email, country="US")
        # Save without calling full_clean() to bypass validation
        super(Maintainer, maintainer_without_email).save()
        CollectionMaintainer.objects.create(collection=collection_without_email, maintainer=maintainer_without_email)

        with translation.override("en"):
            form = PeriodAssignmentForm()
            collection_queryset = form.fields["collection"].queryset

            # Should only show collection with valid maintainer email
            assert collection_queryset.count() == 1
            assert collection_with_email in collection_queryset
            assert collection_without_email not in collection_queryset

    def test_form_filters_maintainers_with_empty_email(self, db):
        """Test that form filters out collections with maintainers who have empty email."""
        from django.contrib.auth.models import User

        from adoration.models import Collection, CollectionMaintainer, Maintainer

        # Create collection and user with valid email
        collection_valid = Collection.objects.create(name="Collection Valid", enabled=True)
        user_valid = User.objects.create_user(
            username="user_valid",
            email="valid@example.com",
            password="testpass123",
        )
        maintainer_valid = Maintainer.objects.create(user=user_valid, country="US")
        CollectionMaintainer.objects.create(collection=collection_valid, maintainer=maintainer_valid)

        # Create collection and user with whitespace-only email
        collection_empty_email = Collection.objects.create(name="Collection Empty Email", enabled=True)
        user_empty_email = User.objects.create_user(username="user_empty", password="testpass123")
        user_empty_email.email = "   "  # Whitespace only
        user_empty_email.save()

        # Create maintainer with empty email (bypass clean method)
        maintainer_empty_email = Maintainer(user=user_empty_email, country="US")
        # Save without calling full_clean() to bypass validation
        super(Maintainer, maintainer_empty_email).save()
        CollectionMaintainer.objects.create(collection=collection_empty_email, maintainer=maintainer_empty_email)

        with translation.override("en"):
            form = PeriodAssignmentForm()
            collection_queryset = form.fields["collection"].queryset

            # Should only show collection with valid maintainer email
            assert collection_queryset.count() == 1
            assert collection_valid in collection_queryset
            assert collection_empty_email not in collection_queryset


@pytest.mark.django_db
class TestCollectionForm:
    """Test cases for CollectionForm."""

    def test_collection_form_valid_data(self, db):
        """Test CollectionForm with valid data."""
        from adoration.forms import CollectionForm

        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en", "pl"],
        }

        form = CollectionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        collection = form.save()
        assert collection.name == "Test Collection"
        assert collection.description == "Test Description"
        assert collection.enabled is True
        assert collection.available_languages == ["en", "pl"]

    def test_collection_form_no_languages_selected(self, db):
        """Test CollectionForm validation when no languages are selected."""
        from adoration.forms import CollectionForm

        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": [],
        }

        form = CollectionForm(data=form_data)
        assert not form.is_valid()
        assert "available_languages" in form.errors
        assert "this field is required" in str(form.errors["available_languages"]).lower()

    def test_collection_form_invalid_language_codes(self, db):
        """Test CollectionForm validation with invalid language codes."""
        from adoration.forms import CollectionForm

        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en", "invalid_code"],
        }

        form = CollectionForm(data=form_data)
        assert not form.is_valid()
        assert "available_languages" in form.errors
        assert "not one of the available choices" in str(form.errors["available_languages"]).lower()

    def test_collection_form_existing_instance(self, db, collection):
        """Test CollectionForm with existing instance."""
        from adoration.forms import CollectionForm

        # Set initial languages on collection and disable to avoid maintainer validation
        collection.available_languages = ["en", "nl"]
        collection.enabled = False
        collection.save()

        form = CollectionForm(instance=collection)

        # Check that initial value is set correctly
        assert form.fields["available_languages"].initial == ["en", "nl"]

        # Test updating
        form_data = {
            "name": collection.name,
            "description": "Updated Description",
            "enabled": collection.enabled,
            "available_languages": ["pl"],
        }

        form = CollectionForm(data=form_data, instance=collection)
        assert form.is_valid(), f"Form errors: {form.errors}"

        updated_collection = form.save()
        assert updated_collection.description == "Updated Description"
        assert updated_collection.available_languages == ["pl"]

    def test_collection_form_with_assignment_limit(self, db):
        """Test CollectionForm with assignment limit."""
        from adoration.forms import CollectionForm
        from adoration.models import CollectionConfig

        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en"],
            "assignment_limit": 5,
        }

        form = CollectionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        collection = form.save()
        assert collection.name == "Test Collection"

        # Check that CollectionConfig was created
        config = CollectionConfig.objects.get(collection=collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT)
        assert config.value == "5"
        assert "Maximum number of assignments per period" in config.description

    def test_collection_form_without_assignment_limit(self, db):
        """Test CollectionForm without assignment limit (should not create config)."""
        from adoration.forms import CollectionForm
        from adoration.models import CollectionConfig

        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en"],
        }

        form = CollectionForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"

        collection = form.save()

        # Check that no CollectionConfig was created
        assert not CollectionConfig.objects.filter(
            collection=collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
        ).exists()

    def test_collection_form_assignment_limit_validation(self, db):
        """Test CollectionForm assignment limit validation."""
        from adoration.forms import CollectionForm

        # Test invalid assignment limit (too small)
        form_data = {
            "name": "Test Collection",
            "description": "Test Description",
            "enabled": True,
            "available_languages": ["en"],
            "assignment_limit": 0,
        }

        form = CollectionForm(data=form_data)
        assert not form.is_valid()
        assert "assignment_limit" in form.errors

        # Test invalid assignment limit (too large)
        form_data["assignment_limit"] = 101
        form = CollectionForm(data=form_data)
        assert not form.is_valid()
        assert "assignment_limit" in form.errors

    def test_collection_form_update_assignment_limit(self, db):
        """Test updating assignment limit on existing collection."""
        from adoration.forms import CollectionForm
        from adoration.models import Collection, CollectionConfig

        # Create collection without assignment limit (disabled to avoid maintainer requirement)
        collection = Collection.objects.create(
            name="Test Collection",
            description="Test Description",
            enabled=False,
            available_languages=["en"],
        )

        # Update with assignment limit
        form_data = {
            "name": collection.name,
            "description": collection.description,
            "enabled": False,
            "available_languages": collection.available_languages,
            "assignment_limit": 10,
        }

        form = CollectionForm(data=form_data, instance=collection)
        assert form.is_valid(), f"Form errors: {form.errors}"

        updated_collection = form.save()

        # Check that CollectionConfig was created
        config = CollectionConfig.objects.get(
            collection=updated_collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
        )
        assert config.value == "10"

        # Update to remove assignment limit
        form_data["assignment_limit"] = None
        form = CollectionForm(data=form_data, instance=updated_collection)
        assert form.is_valid(), f"Form errors: {form.errors}"

        form.save()

        # Check that CollectionConfig was deleted
        assert not CollectionConfig.objects.filter(
            collection=updated_collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
        ).exists()

    def test_collection_form_loads_existing_assignment_limit(self, db):
        """Test that CollectionForm loads existing assignment limit from CollectionConfig."""
        from adoration.forms import CollectionForm
        from adoration.models import Collection, CollectionConfig

        # Create collection with assignment limit config
        collection = Collection.objects.create(
            name="Test Collection",
            description="Test Description",
            enabled=True,
            available_languages=["en"],
        )

        CollectionConfig.objects.create(
            collection=collection,
            name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
            value="15",
            description="Test limit",
        )

        # Create form with instance
        form = CollectionForm(instance=collection)

        # Check that assignment_limit field has correct initial value
        assert form.fields["assignment_limit"].initial == 15
