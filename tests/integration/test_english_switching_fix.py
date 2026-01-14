"""
Test suite for English language switching bug fix.

This test module specifically tests the fix for the issue where clicking
the English language button from non-English pages would not change the page
because the URLs were incorrectly generated with language prefixes.
"""

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import translation

from adoration.models import Collection, Period, PeriodAssignment
from adoration.templatetags.language_tags import language_switcher


class TestEnglishLanguageSwitchingFix:
    """Test suite for English language switching bug fix."""

    def setup_method(self):
        """Set up test data before each test method."""
        self.factory = RequestFactory()

        # Create test collection and period for deletion page tests
        self.collection = Collection.objects.create(
            name="Test Collection",
            description="Test collection for language switching",
            enabled=True,
        )

        self.period = Period.objects.create(
            name="Test Period",
        )

        # Create period collection
        from adoration.models import PeriodCollection

        self.period_collection = PeriodCollection.objects.create(
            collection=self.collection,
            period=self.period,
        )

        # Create test assignment with deletion token
        self.assignment = PeriodAssignment.create_with_email(
            email="user@example.com",
            period_collection=self.period_collection,
        )
        self.assignment.save()

    @pytest.mark.django_db
    def test_english_switching_from_polish_deletion_page(self):
        """
        Test that switching to English from Polish deletion page works correctly.

        This is the main bug fix test - previously, the English URL would
        incorrectly contain the /pl/ prefix, making it appear like nothing happened.
        """
        # Create request for Polish deletion page
        request = self.factory.get(f"/pl/delete/{self.assignment.deletion_token}/")
        request.resolver_match = type(
            "obj",
            (object,),
            {
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
        )()

        # Test language switcher in Polish context
        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            # Find English and Polish URLs
            english_url = None
            polish_url = None

            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                elif lang["code"] == "pl":
                    polish_url = lang["next_url"]

            # Verify URLs are generated correctly
            assert english_url is not None, "English URL should be generated"
            assert polish_url is not None, "Polish URL should be generated"

            # Main assertion: English URL should NOT contain /pl/ prefix
            assert "/pl/" not in english_url, f"English URL should not contain /pl/ prefix: {english_url}"

            # English URL should be the non-prefixed version
            expected_english_url = f"/delete/{self.assignment.deletion_token}/"
            assert english_url == expected_english_url, f"Expected {expected_english_url}, got {english_url}"

            # Polish URL should retain the /pl/ prefix
            expected_polish_url = f"/pl/delete/{self.assignment.deletion_token}/"
            assert polish_url == expected_polish_url, f"Expected {expected_polish_url}, got {polish_url}"

            # URLs should be different (this was the bug - they were the same)
            assert english_url != polish_url, "English and Polish URLs must be different"

    @pytest.mark.django_db
    def test_english_switching_from_dutch_deletion_page(self):
        """
        Test that switching to English from Dutch deletion page works correctly.

        This ensures the fix works for all non-English languages, not just Polish.
        """
        # Create request for Dutch deletion page
        request = self.factory.get(f"/nl/delete/{self.assignment.deletion_token}/")
        request.resolver_match = type(
            "obj",
            (object,),
            {
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
        )()

        # Test language switcher in Dutch context
        with translation.override("nl"):
            context = {"request": request}
            result = language_switcher(context)

            # Find English and Dutch URLs
            english_url = None
            dutch_url = None

            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                elif lang["code"] == "nl":
                    dutch_url = lang["next_url"]

            # Verify URLs are generated correctly
            assert english_url is not None, "English URL should be generated"
            assert dutch_url is not None, "Dutch URL should be generated"

            # Main assertion: English URL should NOT contain /nl/ prefix
            assert "/nl/" not in english_url, f"English URL should not contain /nl/ prefix: {english_url}"

            # English URL should be the non-prefixed version
            expected_english_url = f"/delete/{self.assignment.deletion_token}/"
            assert english_url == expected_english_url, f"Expected {expected_english_url}, got {english_url}"

            # Dutch URL should retain the /nl/ prefix
            expected_dutch_url = f"/nl/delete/{self.assignment.deletion_token}/"
            assert dutch_url == expected_dutch_url, f"Expected {expected_dutch_url}, got {dutch_url}"

            # URLs should be different
            assert english_url != dutch_url, "English and Dutch URLs must be different"

    @pytest.mark.django_db
    def test_english_switching_from_polish_registration_page(self):
        """
        Test that switching to English from Polish registration page works correctly.
        """
        # Create request for Polish registration page
        request = self.factory.get("/pl/")
        request.resolver_match = type(
            "obj",
            (object,),
            {"url_name": "registration", "kwargs": {}},
        )()

        # Test language switcher in Polish context
        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            # Find English and Polish URLs
            english_url = None
            polish_url = None

            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                elif lang["code"] == "pl":
                    polish_url = lang["next_url"]

            # Verify URLs are generated correctly
            assert english_url == "/", f"Expected /, got {english_url}"
            assert polish_url == "/pl/", f"Expected /pl/, got {polish_url}"
            assert english_url != polish_url, "English and Polish URLs must be different"

    @pytest.mark.django_db
    def test_english_switching_from_dutch_registration_page(self):
        """
        Test that switching to English from Dutch registration page works correctly.
        """
        # Create request for Dutch registration page
        request = self.factory.get("/nl/")
        request.resolver_match = type(
            "obj",
            (object,),
            {"url_name": "registration", "kwargs": {}},
        )()

        # Test language switcher in Dutch context
        with translation.override("nl"):
            context = {"request": request}
            result = language_switcher(context)

            # Find English and Dutch URLs
            english_url = None
            dutch_url = None

            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                elif lang["code"] == "nl":
                    dutch_url = lang["next_url"]

            # Verify URLs are generated correctly
            assert english_url == "/", f"Expected /, got {english_url}"
            assert dutch_url == "/nl/", f"Expected /nl/, got {dutch_url}"
            assert english_url != dutch_url, "English and Dutch URLs must be different"

    @pytest.mark.django_db
    def test_english_url_never_has_language_prefix(self):
        """
        Test that English URLs never have any language prefix, regardless of context.

        This is a comprehensive test that checks multiple scenarios to ensure
        English URLs are always clean without language prefixes.
        """
        test_scenarios = [
            {
                "name": "Polish deletion page",
                "path": f"/pl/delete/{self.assignment.deletion_token}/",
                "current_lang": "pl",
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
            {
                "name": "Dutch deletion page",
                "path": f"/nl/delete/{self.assignment.deletion_token}/",
                "current_lang": "nl",
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
            {
                "name": "Polish registration page",
                "path": "/pl/",
                "current_lang": "pl",
                "url_name": "registration",
                "kwargs": {},
            },
            {
                "name": "Dutch registration page",
                "path": "/nl/",
                "current_lang": "nl",
                "url_name": "registration",
                "kwargs": {},
            },
        ]

        for scenario in test_scenarios:
            # Create request
            request = self.factory.get(scenario["path"])
            request.resolver_match = type(
                "obj",
                (object,),
                {"url_name": scenario["url_name"], "kwargs": scenario["kwargs"]},
            )()

            # Test language switcher
            with translation.override(scenario["current_lang"]):
                context = {"request": request}
                result = language_switcher(context)

                # Find English URL
                english_url = None
                for lang in result["available_languages"]:
                    if lang["code"] == "en":
                        english_url = lang["next_url"]
                        break

                assert english_url is not None, f"English URL should be generated for {scenario['name']}"

                # Assert English URL has no language prefixes
                assert not english_url.startswith(
                    "/en/"
                ), f"English URL should not start with /en/ in {scenario['name']}: {english_url}"
                assert not english_url.startswith(
                    "/pl/"
                ), f"English URL should not start with /pl/ in {scenario['name']}: {english_url}"
                assert not english_url.startswith(
                    "/nl/"
                ), f"English URL should not start with /nl/ in {scenario['name']}: {english_url}"

                # Assert English URL starts with /
                assert english_url.startswith(
                    "/"
                ), f"English URL should start with / in {scenario['name']}: {english_url}"

    @pytest.mark.django_db
    def test_language_switcher_url_uniqueness(self):
        """
        Test that all language switch URLs are unique for each language.

        This ensures that the bug where English and Polish URLs were identical
        doesn't regress.
        """
        # Test from Polish deletion page
        request = self.factory.get(f"/pl/delete/{self.assignment.deletion_token}/")
        request.resolver_match = type(
            "obj",
            (object,),
            {
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
        )()

        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            # Collect all URLs
            urls = []
            for lang in result["available_languages"]:
                urls.append(lang["next_url"])

            # Assert all URLs are unique
            assert len(urls) == len(set(urls)), f"All language switch URLs should be unique. Got: {urls}"

            # Assert we have the expected number of languages
            assert len(urls) == 3, f"Should have 3 language options, got {len(urls)}"

    @pytest.mark.django_db
    def test_english_switching_preserves_url_structure(self):
        """
        Test that English switching preserves the correct URL structure.

        This ensures that the English URL has the right path structure
        without language prefixes but maintains the correct path.
        """
        # Test deletion page URL structure
        request = self.factory.get(f"/pl/delete/{self.assignment.deletion_token}/")
        request.resolver_match = type(
            "obj",
            (object,),
            {
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
        )()

        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            english_url = None
            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                    break

            # Verify URL structure
            assert english_url is not None, "English URL should be generated"
            assert english_url.startswith("/delete/"), "English URL should start with /delete/"
            assert english_url.endswith(f"/{self.assignment.deletion_token}/"), "English URL should end with token"
            assert english_url.count("/delete/") == 1, "English URL should have exactly one /delete/ segment"

    @pytest.mark.django_db
    def test_form_submission_compatibility(self):
        """
        Test that the generated URLs are compatible with Django's i18n form submission.

        This ensures that the URLs we generate can be properly used as 'next'
        parameters in the language switching form.
        """
        # Test from Polish deletion page
        request = self.factory.get(f"/pl/delete/{self.assignment.deletion_token}/")
        request.resolver_match = type(
            "obj",
            (object,),
            {
                "url_name": "delete_assignment",
                "kwargs": {"token": self.assignment.deletion_token},
            },
        )()

        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            for lang in result["available_languages"]:
                next_url = lang["next_url"]

                # Assert URL is valid for form submission
                assert next_url.startswith("/"), f"URL should be absolute path: {next_url}"
                assert " " not in next_url, f"URL should not contain spaces: {next_url}"
                assert "\n" not in next_url, f"URL should not contain newlines: {next_url}"

                # Assert URL doesn't have double slashes (except after protocol)
                assert "//" not in next_url.replace("://", ""), f"URL should not have double slashes: {next_url}"

    @pytest.mark.django_db
    def test_error_handling_with_malformed_request(self):
        """
        Test that the language switcher handles edge cases gracefully.
        """
        # Test with missing resolver_match
        request = self.factory.get(f"/pl/delete/{self.assignment.deletion_token}/")
        # Deliberately not setting request.resolver_match

        with translation.override("pl"):
            context = {"request": request}
            result = language_switcher(context)

            # Should still generate fallback URLs
            assert "available_languages" in result
            assert len(result["available_languages"]) == 3

            english_url = None
            for lang in result["available_languages"]:
                if lang["code"] == "en":
                    english_url = lang["next_url"]
                    break

            # Should fallback to root for English
            assert english_url == "/", f"Should fallback to / for English, got {english_url}"
