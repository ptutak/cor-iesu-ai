"""
Unit tests for adoration models.

This module contains comprehensive tests for all models in the adoration app,
including validation, relationships, and custom methods.
"""

import hashlib
import secrets

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

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


class TestConfig:
    """Test cases for Config model."""

    def test_config_creation(self, db):
        """Test creating a config object."""
        config = Config.objects.create(
            name=Config.DefaultValues.ASSIGNMENT_LIMIT,
            value="10",
            description="Test config",
        )
        assert config.name == Config.DefaultValues.ASSIGNMENT_LIMIT
        assert config.value == "10"
        assert config.description == "Test config"

    def test_config_unique_name(self, db):
        """Test that config names must be unique."""
        Config.objects.create(name="TEST_CONFIG", value="value1", description="First config")

        with pytest.raises(IntegrityError):
            Config.objects.create(name="TEST_CONFIG", value="value2", description="Duplicate config")

    def test_config_default_values_enum(self):
        """Test that default values enum contains expected values."""
        assert hasattr(Config.DefaultValues, "ASSIGNMENT_LIMIT")
        assert hasattr(Config.DefaultValues, "EMAIL_HOST")
        assert hasattr(Config.DefaultValues, "DEFAULT_FROM_EMAIL")
        assert Config.DefaultValues.ASSIGNMENT_LIMIT == "ASSIGNMENT_LIMIT"


class TestPeriod:
    """Test cases for Period model."""

    def test_period_creation(self, period):
        """Test creating a period using fixture."""
        assert period.name == "Morning Prayer"
        assert "6:00 AM" in period.description
        assert str(period) == "Morning Prayer"

    def test_period_unique_name(self, db):
        """Test that period names must be unique."""
        Period.objects.create(name="Test Period", description="First")

        with pytest.raises(IntegrityError):
            Period.objects.create(name="Test Period", description="Duplicate")

    def test_period_optional_description(self, db):
        """Test that description is optional."""
        period = Period.objects.create(name="No Description Period")
        assert period.description is None or period.description == ""


class TestCollection:
    """Test cases for Collection model."""

    def test_collection_creation(self, collection):
        """Test creating a collection using fixture."""
        assert collection.name == "Weekly Adoration"
        assert collection.enabled is True
        assert str(collection) == "Weekly Adoration"

    def test_collection_disabled(self, disabled_collection):
        """Test disabled collection."""
        assert disabled_collection.enabled is False

    def test_collection_unique_name(self, db):
        """Test that collection names must be unique."""
        Collection.objects.create(name="Test Collection", enabled=True)

        with pytest.raises(ValidationError):
            Collection.objects.create(name="Test Collection", enabled=False)

    def test_collection_clean_validation(self, db, maintainer_user):
        """Test collection validation with maintainers."""
        collection = Collection.objects.create(name="Test Collection", enabled=False)

        # Create maintainer
        maintainer = Maintainer.objects.create(user=maintainer_user, country="Test Country")
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        # Should not raise error when enabling with maintainer
        collection.enabled = True
        collection.clean()
        collection.save()
        assert collection.enabled is True

    def test_collection_save_calls_clean(self, db):
        """Test that save method calls full_clean."""
        collection = Collection(name="Test Collection", enabled=True)
        # This should work since clean validation is bypassed for new objects without pk
        collection.save()
        assert collection.pk is not None

    def test_collection_default_languages(self, db):
        """Test that collection gets default languages when created without specifying."""
        collection = Collection.objects.create(name="Test Collection", enabled=True)

        # Should have default languages from settings
        expected_languages = ["en", "pl", "nl"]  # From settings.LANGUAGES
        assert collection.available_languages == expected_languages

    def test_collection_custom_languages(self, db):
        """Test creating collection with custom available languages."""
        custom_languages = ["en", "pl"]
        collection = Collection.objects.create(
            name="Custom Languages Collection",
            enabled=True,
            available_languages=custom_languages,
        )

        assert collection.available_languages == custom_languages

    def test_collection_empty_languages_validation(self, db):
        """Test that collection cannot have empty available_languages."""
        collection = Collection(name="Empty Languages Collection", enabled=True, available_languages=[])

        with pytest.raises(ValidationError) as exc_info:
            collection.full_clean()

        assert "Collection must have at least one available language" in str(exc_info.value)

    def test_collection_invalid_languages_validation(self, db):
        """Test that collection rejects invalid language codes."""
        invalid_languages = ["en", "invalid", "pl"]
        collection = Collection(
            name="Invalid Languages Collection",
            enabled=True,
            available_languages=invalid_languages,
        )

        with pytest.raises(ValidationError) as exc_info:
            collection.full_clean()

        assert "Invalid language codes: invalid" in str(exc_info.value)

    def test_collection_non_list_languages_validation(self, db):
        """Test that available_languages must be a list."""
        collection = Collection(
            name="Non-list Languages Collection",
            enabled=True,
            available_languages="en,pl,nl",  # String instead of list
        )

        with pytest.raises(ValidationError) as exc_info:
            collection.full_clean()

        assert "Available languages must be a list" in str(exc_info.value)

    def test_is_available_in_language(self, db):
        """Test is_available_in_language method."""
        collection = Collection.objects.create(name="Test Collection", enabled=True, available_languages=["en", "pl"])

        assert collection.is_available_in_language("en") is True
        assert collection.is_available_in_language("pl") is True
        assert collection.is_available_in_language("nl") is False
        assert collection.is_available_in_language("fr") is False

    def test_is_available_in_language_empty_list(self, db):
        """Test is_available_in_language with empty languages list."""
        collection = Collection(name="Test Collection", enabled=True, available_languages=None)

        assert collection.is_available_in_language("en") is False

    def test_get_available_language_names(self, db):
        """Test get_available_language_names method."""
        collection = Collection.objects.create(name="Test Collection", enabled=True, available_languages=["en", "pl"])

        language_names = collection.get_available_language_names()
        expected = [("en", "English"), ("pl", "Polish")]

        assert language_names == expected

    def test_get_available_language_names_empty(self, db):
        """Test get_available_language_names with empty languages."""
        collection = Collection(name="Test Collection", enabled=True, available_languages=[])

        language_names = collection.get_available_language_names()
        assert language_names == []

    def test_get_available_language_names_invalid_code(self, db):
        """Test get_available_language_names filters out invalid codes."""
        # Create collection bypassing validation for testing
        collection = Collection(
            name="Test Collection",
            enabled=True,
            available_languages=["en", "invalid_code", "pl"],
        )

        language_names = collection.get_available_language_names()
        expected = [("en", "English"), ("pl", "Polish")]

        assert language_names == expected

    def test_get_default_languages_method(self, db):
        """Test _get_default_languages private method."""
        collection = Collection()
        default_languages = collection._get_default_languages()

        expected = ["en", "pl", "nl"]  # From settings.LANGUAGES
        assert default_languages == expected

    def test_collection_save_sets_default_languages(self, db):
        """Test that save method sets default languages if empty."""
        collection = Collection(name="Test Collection", enabled=True)
        # Don't set available_languages
        collection.save()

        expected_languages = ["en", "pl", "nl"]
        assert collection.available_languages == expected_languages

    def test_collection_save_preserves_custom_languages(self, db):
        """Test that save method preserves existing languages."""
        custom_languages = ["en", "pl"]
        collection = Collection(name="Test Collection", enabled=True, available_languages=custom_languages)
        collection.save()

        assert collection.available_languages == custom_languages

    def test_collection_validation_with_different_settings(self, db, monkeypatch):
        """Test validation adapts to different LANGUAGES settings."""
        # Mock settings.LANGUAGES using monkeypatch
        monkeypatch.setattr("django.conf.settings.LANGUAGES", [("en", "English"), ("fr", "French")])

        collection = Collection(
            name="Test Collection",
            enabled=True,
            available_languages=["en", "pl"],  # pl not in mocked settings
        )

        with pytest.raises(ValidationError) as exc_info:
            collection.full_clean()

        assert "Invalid language codes: pl" in str(exc_info.value)
        assert "Valid codes are: en, fr" in str(exc_info.value)


class TestMaintainer:
    """Test cases for Maintainer model."""

    def test_maintainer_creation(self, maintainer):
        """Test creating a maintainer using fixture."""
        assert maintainer.user.username == "maintainer"
        assert maintainer.phone_number == "+1234567890"
        assert maintainer.country == "United States"
        assert "maintainer@example.com" in str(maintainer)

    def test_maintainer_string_representation_with_name(self, maintainer):
        """Test string representation with full name."""
        maintainer.user.first_name = "John"
        maintainer.user.last_name = "Doe"
        maintainer.user.save()
        str_repr = str(maintainer)
        assert "John Doe" in str_repr and "maintainer@example.com" in str_repr

    def test_maintainer_string_representation_without_name(self, db):
        """Test string representation without full name falls back to username."""
        user = User.objects.create_user(username="noname", email="test@example.com")
        maintainer = Maintainer.objects.create(user=user, phone_number="123456789", country="Test Country")
        str_repr = str(maintainer)
        assert "noname" in str_repr and "test@example.com" in str_repr

    def test_maintainer_optional_phone(self, maintainer_user):
        """Test that phone number is optional."""
        maintainer = Maintainer.objects.create(user=maintainer_user, country="Test Country")
        assert maintainer.phone_number == ""

    def test_maintainer_email_validation_valid(self, db):
        """Test that maintainer with valid email is accepted."""
        user = User.objects.create_user(username="valid_user", email="valid@example.com", password="testpass123")
        maintainer = Maintainer(user=user, country="Test Country")

        # Should not raise validation error
        maintainer.full_clean()
        maintainer.save()
        assert maintainer.id is not None

    def test_maintainer_email_validation_no_email(self, db):
        """Test that maintainer without email is rejected."""
        from django.core.exceptions import ValidationError

        user = User.objects.create_user(username="no_email_user", password="testpass123")
        # Ensure no email is set
        user.email = ""
        user.save()

        maintainer = Maintainer(user=user, country="Test Country")

        with pytest.raises(ValidationError) as exc_info:
            maintainer.full_clean()

        assert "Maintainer user must have an email address" in str(exc_info.value)

    def test_maintainer_email_validation_empty_email(self, db):
        """Test that maintainer with empty email is rejected."""
        from django.core.exceptions import ValidationError

        user = User.objects.create_user(
            username="empty_email_user",
            email="   ",  # Whitespace only
            password="testpass123",
        )

        maintainer = Maintainer(user=user, country="Test Country")

        with pytest.raises(ValidationError) as exc_info:
            maintainer.full_clean()

        assert "Maintainer user must have an email address" in str(exc_info.value)

    def test_maintainer_save_calls_validation(self, db):
        """Test that save method calls validation."""
        from django.core.exceptions import ValidationError

        user = User.objects.create_user(username="no_email_save_test", password="testpass123")
        user.email = ""  # Use empty string instead of None
        user.save()

        maintainer = Maintainer(user=user, country="Test Country")

        with pytest.raises(ValidationError):
            maintainer.save()


class TestPeriodCollection:
    """Test cases for PeriodCollection model."""

    def test_period_collection_creation(self, period_collection):
        """Test creating a period collection relationship."""
        assert period_collection.period.name == "Morning Prayer"
        assert period_collection.collection.name == "Weekly Adoration"
        expected_str = f"{period_collection.collection}: {period_collection.period}"
        assert str(period_collection) == expected_str

    def test_period_collection_unique_constraint(self, period, collection):
        """Test that period-collection combinations must be unique."""
        PeriodCollection.objects.create(period=period, collection=collection)

        with pytest.raises(IntegrityError):
            PeriodCollection.objects.create(period=period, collection=collection)


class TestCollectionMaintainer:
    """Test cases for CollectionMaintainer model."""

    def test_collection_maintainer_creation(self, collection_maintainer):
        """Test creating a collection maintainer relationship."""
        assert collection_maintainer.collection.name == "Weekly Adoration"
        assert "maintainer@example.com" in collection_maintainer.maintainer.user.email
        expected_str = f"{collection_maintainer.collection.name} - {collection_maintainer.maintainer.user.email}"
        assert str(collection_maintainer) == expected_str

    def test_collection_maintainer_unique_constraint(self, collection, maintainer):
        """Test that collection-maintainer combinations must be unique."""
        CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)

        with pytest.raises(IntegrityError):
            CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)


class TestCollectionConfig:
    """Test cases for CollectionConfig model."""

    def test_collection_config_creation(self, collection_config):
        """Test creating collection-specific configuration."""
        assert collection_config.collection.name == "Weekly Adoration"
        assert collection_config.name == CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
        assert collection_config.value == "3"
        expected_str = f"{collection_config.collection}: {collection_config.name}"
        assert str(collection_config) == expected_str

    def test_collection_config_unique_constraint(self, collection):
        """Test that collection-config name combinations must be unique."""
        CollectionConfig.objects.create(
            collection=collection,
            name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
            value="5",
        )

        with pytest.raises(IntegrityError):
            CollectionConfig.objects.create(
                collection=collection,
                name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
                value="10",
            )

    def test_collection_config_keys_enum(self):
        """Test that config keys enum contains expected values."""
        assert hasattr(CollectionConfig.ConfigKeys, "ASSIGNMENT_LIMIT")
        assert CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT == "ASSIGNMENT_LIMIT"


class TestPeriodAssignment:
    """Test cases for PeriodAssignment model."""

    def test_period_assignment_creation(self, period_assignment):
        """Test creating a period assignment."""
        assert period_assignment.email_hash != ""
        assert period_assignment.salt != ""
        assert period_assignment.deletion_token != ""
        assert len(period_assignment.deletion_token) == 64  # SHA256 hex

    def test_create_with_email(self, period_collection):
        """Test creating assignment with email."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)

        assert assignment.verify_email(email) is True
        assert assignment.verify_email("wrong@example.com") is False

    def test_create_with_email_and_token(self, period_collection):
        """Test creating assignment with custom deletion token."""
        email = "test@example.com"
        custom_token = "custom-deletion-token-12345"
        assignment = PeriodAssignment.create_with_email(
            email=email,
            period_collection=period_collection,
            deletion_token=custom_token,
        )

        assert assignment.deletion_token == custom_token
        assert assignment.verify_email(email) is True

    def test_email_verification(self, period_collection):
        """Test email verification method."""
        test_email = "participant@example.com"

        # Create new assignment with known email for testing
        assignment = PeriodAssignment.create_with_email(email=test_email, period_collection=period_collection)

        assert assignment.verify_email(test_email) is True
        assert assignment.verify_email("wrong@example.com") is False
        assert assignment.verify_email("") is False

    def test_generate_deletion_token(self, period_collection):
        """Test deletion token generation."""
        assignment = PeriodAssignment(period_collection=period_collection)
        token1 = assignment.generate_deletion_token()
        token2 = assignment.generate_deletion_token()

        # Tokens should be different
        assert token1 != token2
        # Tokens should be 64 characters (SHA256 hex)
        assert len(token1) == 64
        assert len(token2) == 64

    def test_save_generates_token_and_salt(self, period_collection):
        """Test that save method generates token and salt if not provided."""
        assignment = PeriodAssignment(period_collection=period_collection, email_hash="test_hash")
        assignment.save()

        assert assignment.deletion_token != ""
        assert assignment.salt != ""
        assert len(assignment.deletion_token) == 64
        assert len(assignment.salt) == 32

    def test_string_representation(self, period_assignment):
        """Test string representation of assignment."""
        str_repr = str(period_assignment)
        assert "Weekly Adoration: Morning Prayer" in str_repr
        assert "[Hashed Email]" in str_repr

    def test_salt_generation(self, period_collection, monkeypatch):
        """Test salt generation uses secrets module."""

        def mock_token_hex(length):
            return "mocked_salt_12345"

        monkeypatch.setattr("secrets.token_hex", mock_token_hex)

        assignment = PeriodAssignment.create_with_email(email="test@example.com", period_collection=period_collection)
        assignment.save()

        assert assignment.salt == "mocked_salt_12345"

    def test_email_hash_consistency(self, period_collection):
        """Test that email hash is consistent for same email/salt/token combination."""
        email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)

        # Manually create the expected hash using PBKDF2
        from django.contrib.auth.hashers import PBKDF2PasswordHasher

        hasher = PBKDF2PasswordHasher()
        combined_data = f"{email}{assignment.deletion_token}"
        expected_hash = hasher.encode(
            password=combined_data,
            salt=assignment.salt,
            iterations=assignment.iterations,
        )

        assert assignment.email_hash == expected_hash

    def test_assignment_cascade_delete(self, period_assignment, period_collection):
        """Test that assignments are deleted when period_collection is deleted."""
        assignment_id = period_assignment.id
        period_collection.delete()

        assert not PeriodAssignment.objects.filter(id=assignment_id).exists()

    def test_save_without_deletion_token(self, period_collection):
        """Test save method when deletion_token is empty."""
        assignment = PeriodAssignment(period_collection=period_collection)
        assignment.save()

        assert assignment.deletion_token != ""
        assert assignment.salt != ""

    def test_save_with_existing_deletion_token(self, period_collection):
        """Test save method when deletion_token already exists."""
        token = "existing-token-123"
        assignment = PeriodAssignment(period_collection=period_collection, deletion_token=token)
        assignment.save()

        # Should keep the existing token
        assert assignment.deletion_token == token


class TestMaintainerPeriod:
    """Test cases for MaintainerPeriod model."""

    def test_maintainer_period_creation(self, maintainer, period):
        """Test creating a MaintainerPeriod."""
        from adoration.models import MaintainerPeriod

        maintainer_period = MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        assert maintainer_period.maintainer == maintainer
        assert maintainer_period.period == period
        assert maintainer_period.created_at is not None

    def test_maintainer_period_unique_constraint(self, maintainer, period):
        """Test that MaintainerPeriod enforces unique constraint."""
        from django.db import IntegrityError

        from adoration.models import MaintainerPeriod

        # Create first maintainer-period relationship
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Try to create duplicate - should raise IntegrityError
        with pytest.raises(IntegrityError):
            MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

    def test_maintainer_period_string_representation(self, maintainer, period):
        """Test string representation of MaintainerPeriod."""
        from adoration.models import MaintainerPeriod

        maintainer_period = MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        expected = f"{maintainer.user.email} - {period.name}"
        assert str(maintainer_period) == expected

    def test_maintainer_period_cascade_delete_maintainer(self, maintainer, period):
        """Test that deleting maintainer cascades to MaintainerPeriod."""
        from adoration.models import MaintainerPeriod

        maintainer_period = MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Delete maintainer should cascade
        maintainer.delete()

        assert not MaintainerPeriod.objects.filter(id=maintainer_period.id).exists()

    def test_maintainer_period_cascade_delete_period(self, maintainer, period):
        """Test that deleting period cascades to MaintainerPeriod."""
        from adoration.models import MaintainerPeriod

        maintainer_period = MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Delete period should cascade
        period.delete()

        assert not MaintainerPeriod.objects.filter(id=maintainer_period.id).exists()

    def test_maintainer_periods_relationship(self, maintainer):
        """Test many-to-many relationship through MaintainerPeriod."""
        from adoration.models import MaintainerPeriod, Period

        # Create periods
        period1 = Period.objects.create(name="Morning", description="Morning period")
        period2 = Period.objects.create(name="Evening", description="Evening period")

        # Create relationships
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period1)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period2)

        # Test relationship access
        maintainer_periods = maintainer.periods.all()
        assert period1 in maintainer_periods
        assert period2 in maintainer_periods
        assert maintainer_periods.count() == 2
