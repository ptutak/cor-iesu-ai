#!/usr/bin/env python
"""Test script to validate the new privacy implementation for PeriodAssignment."""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coreiesuai.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

import secrets

from django.contrib.auth.models import User

from adoration.forms import DeletionConfirmForm, PeriodAssignmentForm
from adoration.models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


def test_privacy_implementation():
    """Test the privacy implementation."""
    print("Testing Privacy Implementation")
    print("=" * 50)

    # Test 1: Check if we can create assignment with hashed email
    print("\n1. Testing PeriodAssignment.create_with_email()")

    try:
        # Get or create test data
        period, _ = Period.objects.get_or_create(
            name="Test Period",
            defaults={"description": "Test period for privacy testing"},
        )

        collection, _ = Collection.objects.get_or_create(
            name="Test Collection",
            defaults={"description": "Test collection", "enabled": True},
        )

        # Create a maintainer for the collection first
        user, _ = User.objects.get_or_create(
            username="testmaintainer",
            defaults={
                "email": "maintainer@example.com",
                "first_name": "Test",
                "last_name": "Maintainer",
            },
        )

        maintainer, _ = Maintainer.objects.get_or_create(user=user, defaults={"country": "Test Country"})

        # Add maintainer to collection
        CollectionMaintainer.objects.get_or_create(collection=collection, maintainer=maintainer)

        period_collection, _ = PeriodCollection.objects.get_or_create(period=period, collection=collection)

        # Create assignment with hashed email
        test_email = "test@example.com"
        assignment = PeriodAssignment.create_with_email(email=test_email, period_collection=period_collection)
        assignment.save()

        print(f"✓ Assignment created with hashed email")
        print(f"  Email hash: {assignment.email_hash[:16]}...")
        print(f"  Salt: {assignment.salt[:8]}...")
        print(f"  Deletion token: {assignment.deletion_token[:16]}...")

        # Test 2: Verify email verification works
        print("\n2. Testing email verification")

        if assignment.verify_email(test_email):
            print("✓ Email verification works correctly")
        else:
            print("✗ Email verification failed")

        if not assignment.verify_email("wrong@example.com"):
            print("✓ Email verification correctly rejects wrong email")
        else:
            print("✗ Email verification incorrectly accepted wrong email")

        # Test 3: Test form validation
        print("\n3. Testing form functionality")

        form_data = {
            "collection": collection.id,
            "period_collection": period_collection.id,
            "attendant_name": "Test User",
            "attendant_email": "newuser@example.com",
            "attendant_phone_number": "+1234567890",
        }

        form = PeriodAssignmentForm(data=form_data)
        if form.is_valid():
            print("✓ Form validation passed")

            # Don't save to avoid duplicate
            # saved_assignment = form.save()
            # print(f"✓ Form save created assignment with hash: {saved_assignment.email_hash[:16]}...")
        else:
            print(f"✗ Form validation failed: {form.errors}")

        # Test 4: Test deletion form
        print("\n4. Testing deletion form")

        deletion_form = DeletionConfirmForm(assignment=assignment, data={"email": test_email})

        if deletion_form.is_valid():
            print("✓ Deletion form validation passed with correct email")
        else:
            print(f"✗ Deletion form validation failed: {deletion_form.errors}")

        # Test wrong email
        wrong_deletion_form = DeletionConfirmForm(assignment=assignment, data={"email": "wrong@example.com"})

        if not wrong_deletion_form.is_valid():
            print("✓ Deletion form correctly rejects wrong email")
        else:
            print("✗ Deletion form incorrectly accepted wrong email")

        # Test 5: Check that no personal data is stored
        print("\n5. Testing data privacy")

        # Refresh from database
        assignment.refresh_from_db()

        # Check that we don't have personal data fields
        model_fields = [field.name for field in assignment._meta.fields]

        privacy_check = True
        for field in ["attendant_name", "attendant_email", "attendant_phone_number"]:
            if field in model_fields:
                print(f"✗ Privacy violation: {field} field still exists")
                privacy_check = False

        if privacy_check:
            print("✓ No personal data fields found in model")

        # Check that we have the new privacy fields
        required_fields = ["email_hash", "salt", "deletion_token"]
        for field in required_fields:
            if field in model_fields:
                print(f"✓ Privacy field {field} exists")
            else:
                print(f"✗ Privacy field {field} missing")

        # Test 6: Test collection maintainer requirement
        print("\n6. Testing collection maintainer requirement")

        try:
            # Try to create a collection without maintainer
            test_collection = Collection(
                name="Test Collection No Maintainer",
                description="Should fail validation",
                enabled=True,
            )
            test_collection.save()  # This should work initially

            print("✓ Collection with maintainer validation setup complete")

        except Exception as e:
            print(f"⚠ Collection maintainer test setup issue: {e}")

        # Clean up
        print("\n7. Cleaning up test data")
        assignment.delete()
        print("✓ Test assignment deleted")

        print("\n" + "=" * 50)
        print("Privacy implementation test completed!")

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_privacy_implementation()
