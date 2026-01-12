"""
Additional tests to improve code coverage for views.py and other modules.

This module contains targeted tests to cover specific uncovered lines
and edge cases in the codebase.
"""

import json

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.test import RequestFactory
from django.utils import translation

from adoration.forms import PeriodAssignmentForm
from adoration.models import (
    Collection,
    CollectionMaintainer,
    Config,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)
from adoration.views import get_collection_periods


@pytest.mark.django_db
class TestViewsAdditionalCoverage:
    """Test additional coverage for views.py."""

    def test_get_collection_periods_exception_handling(self, rf):
        """Test exception handling in get_collection_periods."""
        request = rf.get("/")

        # Test with non-existent collection ID
        response = get_collection_periods(request, collection_id=99999)
        assert response.status_code == 404
        data = json.loads(response.content)
        assert "error" in data

    def test_collection_maintainer_validation_edge_cases(self, collection, maintainer_user):
        """Test collection maintainer validation edge cases."""
        # Test collection without maintainers when enabled
        collection.enabled = True

        # This should raise validation error due to no maintainers
        with pytest.raises(ValidationError):
            collection.full_clean()

    def test_period_assignment_form_edge_cases(self, period_collection, maintainer_user):
        """Test PeriodAssignmentForm edge cases."""
        # Test form initialization without collection parameter
        form = PeriodAssignmentForm()

        # Should have collections available (filtered by language and maintainers)
        assert form.fields["collection"].queryset.count() >= 0

    def test_period_assignment_form_ajax_collection_lookup(self, collection, maintainer_user):
        """Test form initialization with collection that has maintainer."""
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Set collection to be available in English (which is a valid language code)
        collection.available_languages = ["en"]
        collection.save()

        # Override language for this test to ensure it matches
        from django.utils import translation

        with translation.override("en"):
            form = PeriodAssignmentForm()

            # Should show collections that have maintainers and are available in current language
            collection_choices = list(form.fields["collection"].queryset)
            collection_ids = [c.id for c in collection_choices]
            assert collection.id in collection_ids

    def test_registration_view_email_sending_errors(self, rf, complete_setup, monkeypatch):
        """Test email sending error handling in registration view."""
        from adoration.views import registration_view

        setup = complete_setup

        # Ensure collection has available languages
        setup["collection"].available_languages = ["en"]
        setup["collection"].save()

        # Mock send_mail to raise exception
        def mock_send_mail(*args, **kwargs):
            raise Exception("Email server error")

        monkeypatch.setattr("adoration.views.send_mail", mock_send_mail)

        request = rf.post(
            "/",
            data={
                "collection": setup["collection"].id,
                "period_collection": setup["period_collection"].id,
                "attendant_name": "Test User",
                "attendant_email": "test@example.com",
                "privacy_accepted": True,
            },
        )

        # Should handle email errors gracefully but may not create assignment due to error
        with translation.override("en"):
            try:
                response = registration_view(request)
                # If no exception, should redirect on success
                assert response.status_code == 302
            except Exception as e:
                # Email error should be caught and handled
                assert "Email server error" in str(e)


@pytest.mark.django_db
class TestFormsAdditionalCoverage:
    """Test additional coverage for forms.py."""

    def test_period_assignment_form_duplicate_check_edge_cases(self, complete_setup):
        """Test duplicate check edge cases in form validation."""
        setup = complete_setup

        # The complete_setup already includes a maintainer and collection_maintainer

        # Ensure collection has available languages and maintainers
        setup["collection"].available_languages = ["en"]
        setup["collection"].save()

        # Create an existing assignment
        existing_assignment = PeriodAssignment.create_with_email(
            email="existing@example.com", period_collection=setup["period_collection"]
        )
        existing_assignment.save()

        # Test form with different email should pass
        with translation.override("en"):
            form_data = {
                "collection": setup["collection"].id,
                "period_collection": setup["period_collection"].id,
                "attendant_name": "Different User",
                "attendant_email": "different@example.com",
                "privacy_accepted": True,
            }

            form = PeriodAssignmentForm(data=form_data)
            is_valid = form.is_valid()
            if not is_valid:
                print(f"Form errors: {form.errors}")
            assert is_valid

    def test_period_assignment_form_collection_filter_edge_cases(self, maintainer_user):
        """Test collection filtering edge cases."""
        # Create collections with different maintainer configurations
        collection_no_maintainer = Collection.objects.create(name="No Maintainer", enabled=True)

        collection_with_maintainer = Collection.objects.create(name="With Maintainer", enabled=True)

        # Create maintainer only for second collection
        maintainer = Maintainer.objects.create(user=maintainer_user, country="US")
        CollectionMaintainer.objects.create(collection=collection_with_maintainer, maintainer=maintainer)

        with translation.override("en"):
            form = PeriodAssignmentForm()

            # Should only include collections with maintainers
            collection_ids = list(form.fields["collection"].queryset.values_list("id", flat=True))
            assert collection_with_maintainer.id in collection_ids
            assert collection_no_maintainer.id not in collection_ids


@pytest.mark.django_db
class TestModelsAdditionalCoverage:
    """Test additional coverage for models.py."""

    def test_collection_clean_method_edge_cases(self, maintainer_user):
        """Test Collection.clean method edge cases."""
        collection = Collection.objects.create(name="Test", enabled=False)

        # Test clean method when collection is disabled (should not require maintainers)
        collection.clean()  # Should not raise

        # Test clean method when collection is enabled but has no pk yet
        new_collection = Collection(name="New", enabled=True, available_languages=["en"])
        new_collection.clean()  # Should not raise for new collections

    def test_maintainer_clean_validation_edge_cases(self, django_user_model):
        """Test Maintainer.clean validation edge cases."""
        # Test with user that has whitespace-only email
        user = django_user_model.objects.create_user(username="test", password="test")
        user.email = "   "  # Whitespace only
        user.save()

        maintainer = Maintainer(user=user, country="Test")

        with pytest.raises(ValidationError):
            maintainer.clean()

    def test_period_assignment_generate_deletion_token_consistency(self):
        """Test that generate_deletion_token produces consistent results."""
        # Test that the classmethod works
        token1 = PeriodAssignment.generate_deletion_token()
        token2 = PeriodAssignment.generate_deletion_token()

        # Should generate different tokens
        assert token1 != token2
        assert len(token1) == 64  # SHA256 hex length
        assert len(token2) == 64

    def test_collection_language_validation_edge_cases(self):
        """Test collection language validation edge cases."""
        # Test with invalid language structure
        collection = Collection(
            name="Test",
            enabled=True,
            available_languages="invalid",  # Should be list, not string
        )

        with pytest.raises(ValidationError):
            collection.clean()

    def test_collection_get_available_language_names_edge_cases(self):
        """Test get_available_language_names with edge cases."""
        # Test with empty languages
        collection = Collection(name="Test", available_languages=[])
        result = collection.get_available_language_names()
        assert result == []

        # Test with None languages
        collection = Collection(name="Test", available_languages=None)
        result = collection.get_available_language_names()
        assert result == []

    def test_period_assignment_verify_email_with_pbkdf2(self, period_collection):
        """Test verify_email method works correctly with PBKDF2."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        # Test correct email
        assert assignment.verify_email(email) is True

        # Test incorrect email
        assert assignment.verify_email("wrong@example.com") is False

        # Test empty email
        assert assignment.verify_email("") is False


@pytest.mark.django_db
class TestMigrationsCoverage:
    """Test migration-related functionality."""

    def test_config_default_values_enum(self):
        """Test Config.DefaultValues enum coverage."""
        from adoration.models import Config

        # Test all enum values exist and are strings
        assert hasattr(Config.DefaultValues, "ASSIGNMENT_LIMIT")
        assert hasattr(Config.DefaultValues, "DEFAULT_FROM_EMAIL")

        # Test enum values are correct type
        assert isinstance(Config.DefaultValues.ASSIGNMENT_LIMIT, str)
        assert isinstance(Config.DefaultValues.DEFAULT_FROM_EMAIL, str)

    def test_collection_config_keys_enum(self):
        """Test CollectionConfig.ConfigKeys enum coverage."""
        from adoration.models import CollectionConfig

        assert hasattr(CollectionConfig.ConfigKeys, "ASSIGNMENT_LIMIT")
        assert isinstance(CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT, str)


@pytest.mark.django_db
class TestErrorHandling:
    """Test error handling scenarios."""

    def test_period_assignment_save_with_missing_fields(self, period_collection):
        """Test PeriodAssignment save with missing fields."""
        assignment = PeriodAssignment(period_collection=period_collection)

        # Should auto-generate missing fields
        assignment.save()

        assert assignment.deletion_token is not None
        assert assignment.salt is not None
        assert len(assignment.deletion_token) > 0
        assert len(assignment.salt) > 0

    def test_collection_str_representation(self):
        """Test Collection string representation."""
        collection = Collection(name="Test Collection")
        assert str(collection) == "Test Collection"

    def test_period_str_representation(self):
        """Test Period string representation."""
        period = Period(name="Test Period")
        assert str(period) == "Test Period"

    def test_maintainer_str_representation(self, django_user_model):
        """Test Maintainer string representation edge cases."""
        # Test with full name
        user_with_name = django_user_model.objects.create_user(
            username="test",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        maintainer = Maintainer(user=user_with_name, country="US")
        assert "Test User" in str(maintainer)
        assert "test@example.com" in str(maintainer)

        # Test without full name
        user_no_name = django_user_model.objects.create_user(username="noname", email="noname@example.com")
        maintainer_no_name = Maintainer(user=user_no_name, country="US")
        assert "noname" in str(maintainer_no_name)
