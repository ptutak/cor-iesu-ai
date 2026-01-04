"""Unit tests for adoration.const module."""

import pytest

from adoration.const import DefaultValues, EmailSettings, ValidationMessages


class TestDefaultValues:
    """Test cases for DefaultValues class."""

    def test_assignment_limit_value(self) -> None:
        """Test that ASSIGNMENT_LIMIT has the expected value."""
        assert DefaultValues.ASSIGNMENT_LIMIT == 2

    def test_default_values_class_exists(self) -> None:
        """Test that DefaultValues class can be imported and accessed."""
        # This test ensures the class is properly defined and accessible
        assert hasattr(DefaultValues, "ASSIGNMENT_LIMIT")
        assert isinstance(DefaultValues.ASSIGNMENT_LIMIT, int)

    def test_default_values_class_instantiation(self) -> None:
        """Test that DefaultValues class can be instantiated."""
        # Create an instance of DefaultValues to cover class definition
        instance = DefaultValues()
        assert instance is not None
        assert instance.ASSIGNMENT_LIMIT == 2

    def test_default_values_constant_access(self) -> None:
        """Test accessing constants through class and instance."""
        # Test accessing through class
        class_value = DefaultValues.ASSIGNMENT_LIMIT
        assert class_value == 2

        # Test accessing through instance
        instance = DefaultValues()
        instance_value = instance.ASSIGNMENT_LIMIT
        assert instance_value == 2
        assert class_value == instance_value

    def test_all_default_values_constants(self) -> None:
        """Test all constants in DefaultValues class."""
        assert DefaultValues.ASSIGNMENT_LIMIT == 2
        assert DefaultValues.DEFAULT_EMAIL_TIMEOUT == 30
        assert DefaultValues.MAX_COLLECTION_NAME_LENGTH == 100
        assert DefaultValues.DEFAULT_LANGUAGE == "en"

    def test_email_settings_constants(self) -> None:
        """Test EmailSettings class constants."""
        assert EmailSettings.DEFAULT_FROM_EMAIL == "noreply@example.com"
        assert EmailSettings.EMAIL_SUBJECT_PREFIX == "[Adoration] "

    def test_validation_messages_constants(self) -> None:
        """Test ValidationMessages class constants."""
        assert ValidationMessages.REQUIRED_FIELD == "This field is required."
        assert ValidationMessages.INVALID_EMAIL == "Enter a valid email address."
        assert ValidationMessages.COLLECTION_DISABLED == "This collection is currently disabled."

    def test_const_classes_can_be_instantiated(self) -> None:
        """Test that all const classes can be instantiated."""
        default_values = DefaultValues()
        email_settings = EmailSettings()
        validation_messages = ValidationMessages()

        assert default_values is not None
        assert email_settings is not None
        assert validation_messages is not None
