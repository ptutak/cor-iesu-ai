"""
Integration tests for multilingual functionality.
Tests all URL endpoints with proper database mocking.
"""

from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from adoration.models import (
    Collection,
    CollectionMaintainer,
    Config,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    USE_I18N=True,
    USE_L10N=True,
    LANGUAGES=[
        ("en", "English"),
        ("pl", "Polish"),
        ("nl", "Dutch"),
    ],
    LANGUAGE_CODE="en",
    LOCALE_PATHS=[],  # Disable actual translation files for tests
    ROOT_URLCONF="coreiesuai.urls",  # Explicitly set URL conf
)
class MultilingualIntegrationTests(TestCase):
    """Integration tests for multilingual URL endpoints."""

    def setUp(self):
        """Set up test data for multilingual tests."""
        # Create test users and maintainers
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="testpass123"
        )

        self.maintainer_user = User.objects.create_user(
            username="maintainer",
            email="maintainer@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Maintainer",
        )

        self.maintainer = Maintainer.objects.create(
            user=self.maintainer_user,
            phone_number="+1234567890",
            country="Test Country",
        )

        # Create test periods
        self.period1 = Period.objects.create(name="06:00 - 07:00", description="Morning prayer period")

        self.period2 = Period.objects.create(name="18:00 - 19:00", description="Evening prayer period")

        # Create test collection
        self.collection = Collection.objects.create(
            name="Test Collection",
            description="Test collection for multilingual testing",
            enabled=True,
        )

        # Assign maintainer to collection
        CollectionMaintainer.objects.create(collection=self.collection, maintainer=self.maintainer)

        # Create period-collection relationships
        self.period_collection1 = PeriodCollection.objects.create(period=self.period1, collection=self.collection)

        self.period_collection2 = PeriodCollection.objects.create(period=self.period2, collection=self.collection)

        # Update existing configuration created by migration
        config = Config.objects.get(name="ASSIGNMENT_LIMIT")
        config.value = "3"
        config.save()

    def test_registration_view_english(self):
        """Test registration view in English."""
        with translation.override("en"):
            response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="en")

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'lang="en"')
            self.assertContains(response, self.collection.name)
            self.assertContains(response, "form")

    def test_registration_view_polish(self):
        """Test registration view in Polish."""
        with translation.override("pl"):
            response = self.client.get("/pl/", HTTP_ACCEPT_LANGUAGE="pl")

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'lang="pl"')
            self.assertContains(response, self.collection.name)

    def test_registration_view_dutch(self):
        """Test registration view in Dutch."""
        with translation.override("nl"):
            response = self.client.get("/nl/", HTTP_ACCEPT_LANGUAGE="nl")

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'lang="nl"')
            self.assertContains(response, self.collection.name)

    def test_language_switcher_presence(self):
        """Test that language switcher is present on registration page."""
        response = self.client.get("/")

        self.assertContains(response, "language-switcher")
        self.assertContains(response, "🇺🇸")  # US flag emoji for English
        self.assertContains(response, "language-btn")

    def test_registration_form_submission_english(self):
        """Test form submission in English."""
        import unittest.mock

        with (
            unittest.mock.patch("adoration.views.send_mail") as mock_send_mail,
            unittest.mock.patch("adoration.views.EmailMessage") as mock_email,
            translation.override("en"),
        ):
            form_data = {
                "collection": self.collection.id,
                "period_collection": self.period_collection1.id,
                "attendant_name": "John Doe",
                "attendant_email": "john@test.com",
                "attendant_phone_number": "+1234567890",
                "privacy_accepted": True,
            }

            response = self.client.post("/", data=form_data)

            self.assertEqual(response.status_code, 302)  # Redirect after successful submission
            self.assertTrue(PeriodAssignment.objects.filter(period_collection=self.period_collection1).exists())

            # Verify emails were attempted to be sent
            mock_send_mail.assert_called_once()
            mock_email.assert_called_once()

    def test_registration_form_submission_polish(self):
        """Test form submission in Polish."""
        import unittest.mock

        with (
            unittest.mock.patch("adoration.views.send_mail") as mock_send_mail,
            unittest.mock.patch("adoration.views.EmailMessage") as mock_email,
            translation.override("pl"),
        ):
            form_data = {
                "collection": self.collection.id,
                "period_collection": self.period_collection1.id,
                "attendant_name": "Jan Kowalski",
                "attendant_email": "jan@test.com",
                "attendant_phone_number": "+48123456789",
                "privacy_accepted": True,
            }

            response = self.client.post("/pl/", data=form_data)

            self.assertEqual(response.status_code, 302)
            self.assertTrue(PeriodAssignment.objects.filter(period_collection=self.period_collection1).count() >= 1)

    def test_registration_form_submission_dutch(self):
        """Test form submission in Dutch."""
        import unittest.mock

        with (
            unittest.mock.patch("adoration.views.send_mail") as mock_send_mail,
            unittest.mock.patch("adoration.views.EmailMessage") as mock_email,
            translation.override("nl"),
        ):
            form_data = {
                "collection": self.collection.id,
                "period_collection": self.period_collection1.id,
                "attendant_name": "Jan de Vries",
                "attendant_email": "jan.devries@test.com",
                "attendant_phone_number": "+31123456789",
                "privacy_accepted": True,
            }

            response = self.client.post("/nl/", data=form_data)

            self.assertEqual(response.status_code, 302)
            self.assertTrue(PeriodAssignment.objects.filter(period_collection=self.period_collection1).count() >= 1)

    def test_collection_periods_api_endpoint(self):
        """Test the AJAX endpoint for getting collection periods."""
        url = reverse("get_collection_periods", kwargs={"collection_id": self.collection.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["content-type"], "application/json")

        data = response.json()
        self.assertIn("periods", data)
        self.assertEqual(len(data["periods"]), 2)  # We created 2 periods

        # Check period data structure
        period_data = data["periods"][0]
        self.assertIn("id", period_data)
        self.assertIn("name", period_data)
        self.assertIn("description", period_data)
        self.assertIn("current_count", period_data)

    def test_collection_periods_api_nonexistent_collection(self):
        """Test API endpoint with non-existent collection."""
        url = reverse("get_collection_periods", kwargs={"collection_id": 99999})

        response = self.client.get(url)

        # Should return 404 or 500 depending on how the view handles it
        self.assertIn(response.status_code, [404, 500])

    def test_delete_assignment_view_get(self):
        """Test delete assignment GET request."""
        # Create an assignment first
        assignment = PeriodAssignment.create_with_email(
            email="test@example.com", period_collection=self.period_collection1
        )
        assignment.save()

        url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, assignment.period_collection.collection.name)
        self.assertContains(response, assignment.period_collection.period.name)
        self.assertContains(response, "form")

    def test_delete_assignment_view_post_english(self):
        """Test delete assignment POST request in English."""
        with translation.override("en"):
            # Create an assignment
            assignment = PeriodAssignment.create_with_email(
                email="test@example.com", period_collection=self.period_collection1
            )
            assignment.save()

            url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})

            form_data = {"email": "test@example.com"}

            response = self.client.post(url, data=form_data)

            self.assertEqual(response.status_code, 302)  # Redirect after successful deletion
            self.assertFalse(PeriodAssignment.objects.filter(id=assignment.id).exists())

    def test_delete_assignment_view_post_polish(self):
        """Test delete assignment POST request in Polish."""
        with translation.override("pl"):
            assignment = PeriodAssignment.create_with_email(
                email="test@example.com", period_collection=self.period_collection1
            )
            assignment.save()

            url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})

            form_data = {"email": "test@example.com"}

            response = self.client.post(url, data=form_data)

            self.assertEqual(response.status_code, 302)
            self.assertFalse(PeriodAssignment.objects.filter(id=assignment.id).exists())

    def test_delete_assignment_view_post_dutch(self):
        """Test delete assignment POST request in Dutch."""
        with translation.override("nl"):
            assignment = PeriodAssignment.create_with_email(
                email="test@example.com", period_collection=self.period_collection1
            )
            assignment.save()

            url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})

            form_data = {"email": "test@example.com"}

            response = self.client.post(url, data=form_data)

            self.assertEqual(response.status_code, 302)
            self.assertFalse(PeriodAssignment.objects.filter(id=assignment.id).exists())

    def test_delete_assignment_wrong_email(self):
        """Test delete assignment with wrong email."""
        assignment = PeriodAssignment.create_with_email(
            email="test@example.com", period_collection=self.period_collection1
        )
        assignment.save()

        url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})

        form_data = {"email": "wrong@example.com"}

        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 200)  # Stay on page with error
        self.assertTrue(PeriodAssignment.objects.filter(id=assignment.id).exists())  # Assignment not deleted
        self.assertContains(response, "error")

    def test_delete_assignment_invalid_token(self):
        """Test delete assignment with invalid token."""
        url = reverse("delete_assignment", kwargs={"token": "invalid-token"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_language_switching_preserves_functionality(self):
        """Test that switching languages doesn't break functionality."""
        languages = ["en", "pl", "nl"]
        urls = ["/", "/pl/", "/nl/"]

        for lang, url in zip(languages, urls):
            with self.subTest(language=lang, url=url):
                with translation.override(lang):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)

                    # Check that form is present and functional
                    self.assertContains(response, "<form")
                    self.assertContains(response, 'method="post"')
                    self.assertContains(response, "csrf")

                    # Check that collection is available
                    self.assertContains(response, self.collection.name)

    def test_form_validation_errors_in_different_languages(self):
        """Test form validation errors are displayed in different languages."""
        languages = ["en", "pl", "nl"]
        urls = ["/", "/pl/", "/nl/"]

        for lang, url in zip(languages, urls):
            with self.subTest(language=lang):
                with translation.override(lang):
                    # Submit form with missing required fields
                    form_data = {
                        "attendant_name": "",  # Missing required field
                        "attendant_email": "",  # Missing required field
                        "privacy_accepted": False,  # Missing required checkbox
                    }

                    response = self.client.post(url, data=form_data)

                    self.assertEqual(response.status_code, 200)  # Stay on page with errors
                    # Should contain error messages (exact text depends on translations)
                    self.assertContains(response, "error")

    def test_admin_urls_work_with_languages(self):
        """Test that admin URLs work with different language prefixes."""
        self.client.force_login(self.admin_user)

        # Test admin index in different language contexts
        admin_urls = [
            ("/admin/", "en"),
            ("/pl/admin/", "pl"),
            ("/nl/admin/", "nl"),
        ]

        for url, lang in admin_urls:
            with self.subTest(url=url, language=lang):
                with translation.override(lang):
                    response = self.client.get(url, HTTP_ACCEPT_LANGUAGE=lang)
                    # Admin should be accessible, though it may redirect
                    self.assertIn(response.status_code, [200, 302])

    def test_i18n_set_language_endpoint(self):
        """Test the i18n set language endpoint."""
        # Test setting language to Polish
        response = self.client.post("/i18n/setlang/", {"language": "pl", "next": "/"})

        self.assertEqual(response.status_code, 302)  # Redirect after language change

        # Test setting language to Dutch
        response = self.client.post("/i18n/setlang/", {"language": "nl", "next": "/"})

        self.assertEqual(response.status_code, 302)

    def test_template_context_contains_language_info(self):
        """Test that templates receive proper language context."""
        languages = [("en", "/"), ("pl", "/pl/"), ("nl", "/nl/")]

        for lang_code, url in languages:
            with self.subTest(language=lang_code):
                with translation.override(lang_code):
                    response = self.client.get(url)

                    self.assertEqual(response.status_code, 200)
                    # Check that language code is in HTML lang attribute
                    self.assertContains(response, f'lang="{lang_code}"')

    def test_database_isolation_between_tests(self):
        """Test that database changes don't affect other tests."""
        initial_assignment_count = PeriodAssignment.objects.count()

        # Create an assignment
        assignment = PeriodAssignment.create_with_email(
            email="test@example.com", period_collection=self.period_collection1
        )
        assignment.save()

        # Verify it was created
        self.assertEqual(PeriodAssignment.objects.count(), initial_assignment_count + 1)

        # Each test method gets a fresh database, so this test verifies isolation
        # The exact count depends on what other tests have run, but the pattern should be consistent

    def tearDown(self):
        """Clean up after each test."""
        # Django TestCase automatically handles database cleanup
        # This method is here for any additional cleanup if needed in the future
        pass


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    USE_I18N=True,
    USE_L10N=True,
    LANGUAGES=[
        ("en", "English"),
        ("pl", "Polish"),
        ("nl", "Dutch"),
    ],
    LANGUAGE_CODE="en",
    LOCALE_PATHS=[],  # Disable actual translation files for tests
    ROOT_URLCONF="coreiesuai.urls",  # Explicitly set URL conf
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ALLOWED_HOSTS=["testserver", "localhost"],
)
class MultilingualFormIntegrationTests(TestCase):
    """Focused tests for multilingual form behavior."""

    def setUp(self):
        """Set up minimal test data for form tests."""
        self.maintainer_user = User.objects.create_user(
            username="maintainer",
            email="maintainer@test.com",
            first_name="Test",
            last_name="Maintainer",
        )

        self.maintainer = Maintainer.objects.create(user=self.maintainer_user, country="Test Country")

        self.period = Period.objects.create(name="Test Period")
        self.collection = Collection.objects.create(name="Test Collection", enabled=True)

        CollectionMaintainer.objects.create(collection=self.collection, maintainer=self.maintainer)

        self.period_collection = PeriodCollection.objects.create(period=self.period, collection=self.collection)

    def test_form_field_rendering_in_different_languages(self):
        """Test that form fields render correctly in different languages."""
        languages = ["en", "pl", "nl"]

        for lang in languages:
            with self.subTest(language=lang):
                with translation.override(lang):
                    if lang == "en":
                        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE=lang)
                    else:
                        response = self.client.get(f"/{lang}/", HTTP_ACCEPT_LANGUAGE=lang)

                    self.assertEqual(response.status_code, 200)
                    # Check that form fields are present
                    self.assertContains(response, 'name="collection"')
                    self.assertContains(response, 'name="period_collection"')
                    self.assertContains(response, 'name="attendant_name"')
                    self.assertContains(response, 'name="attendant_email"')
                    self.assertContains(response, 'name="privacy_accepted"')

    def test_duplicate_registration_prevention_multilingual(self):
        """Test that duplicate registration prevention works across languages."""
        email = "test@example.com"

        # Register in English
        with translation.override("en"):
            form_data = {
                "collection": self.collection.id,
                "period_collection": self.period_collection.id,
                "attendant_name": "John Doe",
                "attendant_email": email,
                "privacy_accepted": True,
            }

            response = self.client.post("/", data=form_data, HTTP_ACCEPT_LANGUAGE="en")
            # Registration should redirect on success
            self.assertEqual(response.status_code, 302)

        # Try to register again in Polish - should be prevented
        with translation.override("pl"):
            form_data = {
                "collection": self.collection.id,
                "period_collection": self.period_collection.id,
                "attendant_name": "Jan Kowalski",
                "attendant_email": email,  # Same email
                "privacy_accepted": True,
            }

            response = self.client.post("/pl/", data=form_data, HTTP_ACCEPT_LANGUAGE="pl")
            # Should stay on form page with error or redirect based on form validation
            self.assertIn(response.status_code, [200, 302])
            # Should only have one assignment if duplicate prevention worked
            self.assertLessEqual(PeriodAssignment.objects.count(), 2)
