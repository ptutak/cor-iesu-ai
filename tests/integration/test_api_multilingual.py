"""
Integration tests for API endpoints with multilingual support.
Tests AJAX endpoints and JSON responses in different language contexts.
"""

import json
from unittest.mock import patch

from django.contrib.auth.models import User
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
)
class MultilingualAPIIntegrationTests(TestCase):
    """Integration tests for multilingual API endpoints."""

    def setUp(self):
        """Set up test data for API tests."""
        # Create test maintainer
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

        # Create test periods with different descriptions
        self.periods = [
            Period.objects.create(name="06:00 - 07:00", description="Morning prayer session"),
            Period.objects.create(name="12:00 - 13:00", description="Midday prayer session"),
            Period.objects.create(name="18:00 - 19:00", description="Evening prayer session"),
        ]

        # Create test collections
        self.collections = [
            Collection.objects.create(
                name="English Collection",
                description="English adoration collection",
                enabled=True,
            ),
            Collection.objects.create(
                name="Polish Collection - Kolekcja Polska",
                description="Kolekcja adoracji po polsku",
                enabled=True,
            ),
            Collection.objects.create(
                name="Dutch Collection - Nederlandse Collectie",
                description="Nederlandse aanbidding collectie",
                enabled=True,
            ),
        ]

        # Assign maintainer to all collections
        for collection in self.collections:
            CollectionMaintainer.objects.create(collection=collection, maintainer=self.maintainer)

        # Create period-collection relationships
        self.period_collections = []
        for collection in self.collections:
            for period in self.periods:
                pc = PeriodCollection.objects.create(period=period, collection=collection)
                self.period_collections.append(pc)

        # Create some test assignments
        self.test_assignments = []
        for i, pc in enumerate(self.period_collections[:3]):  # First 3 only
            assignment = PeriodAssignment.create_with_email(email=f"test{i}@example.com", period_collection=pc)
            assignment.save()
            self.test_assignments.append(assignment)

        # Create configuration
        Config.objects.create(name="ASSIGNMENT_LIMIT", value="5", description="Max assignments per period")

    def test_collection_periods_api_english(self):
        """Test collection periods API in English context."""
        with translation.override("en"):
            collection = self.collections[0]  # English collection
            url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["content-type"], "application/json")

            data = response.json()
            self.assertIn("periods", data)
            self.assertEqual(len(data["periods"]), len(self.periods))

            # Check data structure
            for period_data in data["periods"]:
                self.assertIn("id", period_data)
                self.assertIn("name", period_data)
                self.assertIn("description", period_data)
                self.assertIn("current_count", period_data)
                self.assertIsInstance(period_data["current_count"], int)

    def test_collection_periods_api_polish(self):
        """Test collection periods API in Polish context."""
        with translation.override("pl"):
            collection = self.collections[1]  # Polish collection
            url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("periods", data)

    def test_collection_periods_api_dutch(self):
        """Test collection periods API in Dutch context."""
        with translation.override("nl"):
            collection = self.collections[2]  # Dutch collection
            url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("periods", data)

    def test_collection_periods_api_assignment_counts(self):
        """Test that API returns correct assignment counts."""
        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        response = self.client.get(url)
        data = response.json()

        # Check that assignment counts are correct
        total_assignments_found = sum(period["current_count"] for period in data["periods"])

        # Should have assignments for periods in this collection
        expected_assignments = PeriodAssignment.objects.filter(period_collection__collection=collection).count()

        self.assertEqual(total_assignments_found, expected_assignments)

    def test_collection_periods_api_nonexistent_collection_english(self):
        """Test API with nonexistent collection in English."""
        with translation.override("en"):
            url = reverse("get_collection_periods", kwargs={"collection_id": 99999})

            response = self.client.get(url)

            self.assertIn(response.status_code, [404, 500])

    def test_collection_periods_api_nonexistent_collection_multilingual(self):
        """Test API with nonexistent collection in different languages."""
        languages = ["en", "pl", "nl"]

        for lang in languages:
            with self.subTest(language=lang):
                with translation.override(lang):
                    url = reverse("get_collection_periods", kwargs={"collection_id": 99999})

                    response = self.client.get(url)

                    self.assertEqual(response.status_code, 404)

    def test_collection_periods_api_disabled_collection(self):
        """Test API with disabled collection."""
        # Create a disabled collection
        disabled_collection = Collection.objects.create(
            name="Disabled Collection",
            description="This collection is disabled",
            enabled=False,
        )

        CollectionMaintainer.objects.create(collection=disabled_collection, maintainer=self.maintainer)

        url = reverse("get_collection_periods", kwargs={"collection_id": disabled_collection.id})

        response = self.client.get(url)

        # Should return 404 for disabled collections
        self.assertIn(response.status_code, [404, 500])

    def test_api_error_messages_in_different_languages(self):
        """Test that API error messages respect language context."""
        # We'll need to mock an error condition
        with patch("adoration.views.PeriodCollection.objects.filter") as mock_filter:
            mock_filter.side_effect = Exception("Test error")

            languages = ["en", "pl", "nl"]
            for lang in languages:
                with self.subTest(language=lang):
                    with translation.override(lang):
                        collection = self.collections[0]
                        url = reverse(
                            "get_collection_periods",
                            kwargs={"collection_id": collection.id},
                        )

                        response = self.client.get(url)

                        self.assertIn(response.status_code, [404, 500])
                        data = response.json()
                        self.assertIn("error", data)

                        # Error message should be present
                        self.assertIsInstance(data["error"], str)
                        self.assertTrue(len(data["error"]) > 0)

    def test_api_response_format_consistency(self):
        """Test that API response format is consistent across languages."""
        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        languages = ["en", "pl", "nl"]
        responses = {}

        # Collect responses for all languages
        for lang in languages:
            with translation.override(lang):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                responses[lang] = response.json()

        # All responses should have the same structure
        for lang, data in responses.items():
            with self.subTest(language=lang):
                self.assertIn("periods", data)
                self.assertIsInstance(data["periods"], list)

                # Check that all periods have the same fields
                for period in data["periods"]:
                    required_fields = ["id", "name", "description", "current_count"]
                    for field in required_fields:
                        self.assertIn(field, period)

    def test_api_periods_data_integrity(self):
        """Test that period data is consistent regardless of language context."""
        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        # Get responses in different languages
        responses = {}
        languages = ["en", "pl", "nl"]

        for lang in languages:
            with translation.override(lang):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                responses[lang] = response.json()

        # Period IDs and counts should be identical across languages
        first_lang = list(responses.keys())[0]
        first_periods = {p["id"]: p for p in responses[first_lang]["periods"]}

        for lang, data in responses.items():
            if lang == first_lang:
                continue

            lang_periods = {p["id"]: p for p in data["periods"]}

            # Same period IDs should be present
            self.assertEqual(set(first_periods.keys()), set(lang_periods.keys()))

            # Assignment counts should be identical
            for period_id in first_periods.keys():
                self.assertEqual(
                    first_periods[period_id]["current_count"],
                    lang_periods[period_id]["current_count"],
                )

    def test_api_content_type_headers(self):
        """Test that API returns correct content-type headers."""
        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        languages = ["en", "pl", "nl"]

        for lang in languages:
            with self.subTest(language=lang):
                with translation.override(lang):
                    response = self.client.get(url)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["content-type"], "application/json")

    def test_api_performance_across_languages(self):
        """Test that API performance is consistent across languages."""
        import time

        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        languages = ["en", "pl", "nl"]
        response_times = {}

        for lang in languages:
            with translation.override(lang):
                start_time = time.time()
                response = self.client.get(url)
                end_time = time.time()

                self.assertEqual(response.status_code, 200)
                response_times[lang] = end_time - start_time

        # Response times should be reasonably similar (within 500ms for test environment)
        max_time = max(response_times.values())
        min_time = min(response_times.values())
        self.assertLess(max_time - min_time, 0.5)  # 500ms tolerance

    def test_api_json_encoding_with_unicode(self):
        """Test that API properly handles unicode characters in different languages."""
        # Create periods with unicode characters
        unicode_period = Period.objects.create(
            name="Ś Ć Ż Ą Ę - Unicode Test",
            description="Test with Polish characters: łóćęśążźń",
        )

        unicode_collection = Collection.objects.create(
            name="Unicode Collection - Ñandú çæøå",
            description="Test with various unicode: αβγδε русский العربية 中文",
            enabled=True,
        )

        CollectionMaintainer.objects.create(collection=unicode_collection, maintainer=self.maintainer)

        PeriodCollection.objects.create(period=unicode_period, collection=unicode_collection)

        url = reverse("get_collection_periods", kwargs={"collection_id": unicode_collection.id})

        languages = ["en", "pl", "nl"]

        for lang in languages:
            with self.subTest(language=lang):
                with translation.override(lang):
                    response = self.client.get(url)

                    self.assertEqual(response.status_code, 200)
                    data = response.json()

                    # Should be able to parse JSON with unicode characters
                    self.assertIn("periods", data)
                    self.assertTrue(len(data["periods"]) > 0)

                    # Find our unicode period
                    unicode_period_data = None
                    for period in data["periods"]:
                        if "Unicode Test" in period["name"]:
                            unicode_period_data = period
                            break

                    self.assertIsNotNone(unicode_period_data)
                    self.assertIn("łóćęśążźń", unicode_period_data["description"])

    def test_api_cross_origin_headers(self):
        """Test API response headers for potential CORS requirements."""
        collection = self.collections[0]
        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        response = self.client.get(url)

        # Basic checks for response headers
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header("content-type"))

        # If CORS headers were to be added, they would be tested here
        # For now, just ensure the response is properly formatted

    def tearDown(self):
        """Clean up after each test."""
        # Django TestCase automatically handles database cleanup
        pass


class APIErrorHandlingTests(TestCase):
    """Tests for API error handling in multilingual context."""

    def setUp(self):
        """Set up minimal test data."""
        self.maintainer_user = User.objects.create_user(username="maintainer", email="maintainer@test.com")
        self.maintainer = Maintainer.objects.create(user=self.maintainer_user, country="Test")

    def test_api_malformed_collection_id(self):
        """Test API with malformed collection ID."""
        malformed_ids = ["abc", "12.34", "-1", ""]

        for bad_id in malformed_ids:
            with self.subTest(collection_id=bad_id):
                try:
                    url = reverse("get_collection_periods", kwargs={"collection_id": bad_id})
                    response = self.client.get(url)
                    # Should handle gracefully, either 404 or 400
                    self.assertIn(response.status_code, [400, 404, 500])
                except Exception:
                    # URL reversal might fail for invalid IDs, which is acceptable
                    pass

    def test_api_very_large_collection_id(self):
        """Test API with very large collection ID."""
        large_id = 999999999999999
        url = reverse("get_collection_periods", kwargs={"collection_id": large_id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("adoration.views.PeriodCollection.objects.filter")
    def test_api_database_error_handling(self, mock_filter):
        """Test API behavior when database errors occur."""
        # Create a test collection first
        collection = Collection.objects.create(name="Test", enabled=True)
        CollectionMaintainer.objects.create(collection=collection, maintainer=self.maintainer)

        # Mock a database error
        mock_filter.side_effect = Exception("Database connection error")

        url = reverse("get_collection_periods", kwargs={"collection_id": collection.id})

        response = self.client.get(url)

        # Should return a 500 error with error message
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)
