"""Unit tests for adoration.const module."""

import unittest

from adoration.const import DefaultValues


class TestDefaultValues(unittest.TestCase):
    """Test cases for DefaultValues class."""

    def test_assignment_limit_value(self) -> None:
        """Test that ASSIGNMENT_LIMIT has the expected value."""
        self.assertEqual(DefaultValues.ASSIGNMENT_LIMIT, 2)

    def test_default_values_class_exists(self) -> None:
        """Test that DefaultValues class can be imported and accessed."""
        # This test ensures the class is properly defined and accessible
        self.assertTrue(hasattr(DefaultValues, "ASSIGNMENT_LIMIT"))
        self.assertIsInstance(DefaultValues.ASSIGNMENT_LIMIT, int)

    def test_default_values_class_instantiation(self) -> None:
        """Test that DefaultValues class can be instantiated."""
        # Create an instance of DefaultValues to cover class definition
        instance = DefaultValues()
        self.assertIsNotNone(instance)
        self.assertEqual(instance.ASSIGNMENT_LIMIT, 2)

    def test_default_values_constant_access(self) -> None:
        """Test accessing constants through class and instance."""
        # Test accessing through class
        class_value = DefaultValues.ASSIGNMENT_LIMIT
        self.assertEqual(class_value, 2)

        # Test accessing through instance
        instance = DefaultValues()
        instance_value = instance.ASSIGNMENT_LIMIT
        self.assertEqual(instance_value, 2)
        self.assertEqual(class_value, instance_value)

    def test_all_default_values_constants(self) -> None:
        """Test all constants in DefaultValues class."""
        self.assertEqual(DefaultValues.ASSIGNMENT_LIMIT, 2)
        self.assertEqual(DefaultValues.DEFAULT_EMAIL_TIMEOUT, 30)
        self.assertEqual(DefaultValues.MAX_COLLECTION_NAME_LENGTH, 100)
        self.assertEqual(DefaultValues.DEFAULT_LANGUAGE, "en")

    def test_email_settings_constants(self) -> None:
        """Test EmailSettings class constants."""
        from adoration.const import EmailSettings

        self.assertEqual(EmailSettings.DEFAULT_FROM_EMAIL, "noreply@example.com")
        self.assertEqual(EmailSettings.EMAIL_SUBJECT_PREFIX, "[Adoration] ")

    def test_validation_messages_constants(self) -> None:
        """Test ValidationMessages class constants."""
        from adoration.const import ValidationMessages

        self.assertEqual(ValidationMessages.REQUIRED_FIELD, "This field is required.")
        self.assertEqual(ValidationMessages.INVALID_EMAIL, "Enter a valid email address.")
        self.assertEqual(
            ValidationMessages.COLLECTION_DISABLED,
            "This collection is currently disabled.",
        )

    def test_const_classes_can_be_instantiated(self) -> None:
        """Test that all const classes can be instantiated."""
        from adoration.const import EmailSettings, ValidationMessages

        default_values = DefaultValues()
        email_settings = EmailSettings()
        validation_messages = ValidationMessages()

        self.assertIsNotNone(default_values)
        self.assertIsNotNone(email_settings)
        self.assertIsNotNone(validation_messages)
