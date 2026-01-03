"""Integration tests for privacy implementation in PeriodAssignment."""

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

from adoration.forms import DeletionConfirmForm, PeriodAssignmentForm
from adoration.models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


@pytest.mark.django_db
class PrivacyImplementationTests(TestCase):
    """Test cases for privacy implementation."""

    def setUp(self):
        """Set up test data."""
        # Create test data
        self.period = Period.objects.create(name="Test Period", description="Test period for privacy testing")

        self.collection = Collection.objects.create(
            name="Test Collection",
            description="Test collection",
            enabled=True,
            available_languages=["en", "pl", "nl"],
        )

        # Create a maintainer for the collection
        self.user = User.objects.create_user(
            username="testmaintainer",
            email="maintainer@example.com",
            first_name="Test",
            last_name="Maintainer",
        )

        self.maintainer = Maintainer.objects.create(user=self.user, country="Test Country")

        # Add maintainer to collection
        CollectionMaintainer.objects.create(collection=self.collection, maintainer=self.maintainer)

        self.period_collection = PeriodCollection.objects.create(period=self.period, collection=self.collection)

        self.test_email = "test@example.com"

    def test_privacy_implementation(self):
        """Test the complete privacy implementation."""
        # Test 1: Check if we can create assignment with hashed email
        assignment = PeriodAssignment.create_with_email(email=self.test_email, period_collection=self.period_collection)
        assignment.save()

        # Verify assignment was created with proper fields
        self.assertIsNotNone(assignment.email_hash)
        self.assertIsNotNone(assignment.salt)
        self.assertIsNotNone(assignment.deletion_token)
        self.assertTrue(len(assignment.email_hash) > 0)
        self.assertTrue(len(assignment.salt) > 0)
        self.assertTrue(len(assignment.deletion_token) > 0)

    def test_email_verification(self):
        """Test email verification functionality."""
        assignment = PeriodAssignment.create_with_email(email=self.test_email, period_collection=self.period_collection)
        assignment.save()

        # Test correct email verification
        self.assertTrue(assignment.verify_email(self.test_email))

        # Test wrong email verification
        self.assertFalse(assignment.verify_email("wrong@example.com"))

    def test_form_functionality(self):
        """Test form validation and creation."""
        form_data = {
            "collection": self.collection.id,
            "period_collection": self.period_collection.id,
            "attendant_name": "Test User",
            "attendant_email": "newuser@example.com",
            "attendant_phone_number": "+1234567890",
            "privacy_accepted": True,
        }

        # Test form in English language context
        from django.utils import translation

        with translation.override("en"):
            form = PeriodAssignmentForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Form validation failed: {form.errors}")

    def test_deletion_form(self):
        """Test deletion form validation."""
        assignment = PeriodAssignment.create_with_email(email=self.test_email, period_collection=self.period_collection)
        assignment.save()

        # Test correct email
        deletion_form = DeletionConfirmForm(assignment=assignment, data={"email": self.test_email})
        self.assertTrue(
            deletion_form.is_valid(),
            f"Deletion form validation failed: {deletion_form.errors}",
        )

        # Test wrong email
        wrong_deletion_form = DeletionConfirmForm(assignment=assignment, data={"email": "wrong@example.com"})
        self.assertFalse(wrong_deletion_form.is_valid())

    def test_data_privacy(self):
        """Test that no personal data is stored in the model."""
        assignment = PeriodAssignment.create_with_email(email=self.test_email, period_collection=self.period_collection)
        assignment.save()

        # Refresh from database
        assignment.refresh_from_db()

        # Check that we don't have personal data fields
        model_fields = [field.name for field in assignment._meta.fields]

        # These fields should not exist
        private_fields = ["attendant_name", "attendant_email", "attendant_phone_number"]
        for field in private_fields:
            self.assertNotIn(field, model_fields, f"Privacy violation: {field} field still exists")

        # These fields should exist
        required_fields = ["email_hash", "salt", "deletion_token"]
        for field in required_fields:
            self.assertIn(field, model_fields, f"Privacy field {field} missing")

    def test_unique_tokens_and_hashes(self):
        """Test that each assignment gets unique tokens and hashes."""
        assignment1 = PeriodAssignment.create_with_email(
            email=self.test_email, period_collection=self.period_collection
        )
        assignment1.save()

        assignment2 = PeriodAssignment.create_with_email(
            email="different@example.com", period_collection=self.period_collection
        )
        assignment2.save()

        # Different assignments should have different tokens and hashes
        self.assertNotEqual(assignment1.deletion_token, assignment2.deletion_token)
        self.assertNotEqual(assignment1.email_hash, assignment2.email_hash)
        self.assertNotEqual(assignment1.salt, assignment2.salt)
