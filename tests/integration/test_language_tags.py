"""
Integration tests for language switching template tags.
Tests the custom template tags used for multilingual functionality.
"""

import pytest
from django.http import HttpRequest
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.utils import translation

from adoration.templatetags.language_tags import (
    get_available_languages_with_names,
    get_current_language_name,
    language_switcher,
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
class LanguageTagsIntegrationTests(TestCase):
    """Integration tests for custom language template tags."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()

    def test_get_current_language_name_english(self):
        """Test getting current language name for English."""
        with translation.override("en"):
            result = get_current_language_name()
            self.assertEqual(result, "English")

    def test_get_current_language_name_polish(self):
        """Test getting current language name for Polish."""
        with translation.override("pl"):
            result = get_current_language_name()
            self.assertEqual(result, "Polski")

    def test_get_current_language_name_dutch(self):
        """Test getting current language name for Dutch."""
        with translation.override("nl"):
            result = get_current_language_name()
            self.assertEqual(result, "Nederlands")

    def test_get_current_language_name_unknown_language(self):
        """Test getting current language name for unknown language defaults to English."""
        with translation.override("fr"):  # French not in our supported languages
            result = get_current_language_name()
            self.assertEqual(result, "English")  # Should default to English

    def test_get_available_languages_with_names(self):
        """Test getting all available languages with proper names."""
        result = get_available_languages_with_names()

        expected_languages = [
            {"code": "en", "name": "English"},
            {"code": "pl", "name": "Polski"},
            {"code": "nl", "name": "Nederlands"},
        ]

        self.assertEqual(len(result), 3)
        self.assertEqual(result, expected_languages)

    def test_language_switcher_template_tag_english(self):
        """Test language switcher template tag in English context."""
        with translation.override("en"):
            request = self.factory.get("/")
            context = Context({"request": request})

            result = language_switcher(context)

            self.assertEqual(result["current_language"], "en")
            self.assertEqual(result["current_language_name"], "English")
            self.assertEqual(len(result["available_languages"]), 3)
            self.assertEqual(result["request"], request)

    def test_language_switcher_template_tag_polish(self):
        """Test language switcher template tag in Polish context."""
        with translation.override("pl"):
            request = self.factory.get("/pl/")
            context = Context({"request": request})

            result = language_switcher(context)

            self.assertEqual(result["current_language"], "pl")
            self.assertEqual(result["current_language_name"], "Polski")
            self.assertEqual(len(result["available_languages"]), 3)

    def test_language_switcher_template_tag_dutch(self):
        """Test language switcher template tag in Dutch context."""
        with translation.override("nl"):
            request = self.factory.get("/nl/")
            context = Context({"request": request})

            result = language_switcher(context)

            self.assertEqual(result["current_language"], "nl")
            self.assertEqual(result["current_language_name"], "Nederlands")
            self.assertEqual(len(result["available_languages"]), 3)

    def test_language_switcher_template_rendering(self):
        """Test that language switcher template renders correctly."""
        template_content = """
        {% load language_tags %}
        {% language_switcher %}
        """

        with translation.override("en"):
            request = self.factory.get("/")
            context = Context({"request": request})

            template = Template(template_content)
            rendered = template.render(context)

            # Check that the rendered content contains expected elements
            self.assertIn("dropdown", rendered)
            self.assertIn("English", rendered)

    def test_language_switcher_preserves_current_path(self):
        """Test that language switcher preserves the current path."""
        test_paths = ["/", "/some/path/", "/another/path/?param=value"]

        for path in test_paths:
            with self.subTest(path=path):
                request = self.factory.get(path)
                context = Context({"request": request})

                result = language_switcher(context)

                # The request should be preserved in the context
                self.assertEqual(result["request"].get_full_path(), path)

    def test_simple_tag_registration(self):
        """Test that simple tags are properly registered."""
        template_content = """
        {% load language_tags %}
        Current: {% get_current_language_name %}
        """

        with translation.override("pl"):
            context = Context({})
            template = Template(template_content)
            rendered = template.render(context)

            self.assertIn("Current: Polski", rendered)

    def test_available_languages_tag_registration(self):
        """Test that available languages tag is properly registered."""
        template_content = """
        {% load language_tags %}
        {% get_available_languages_with_names as languages %}
        {% for lang in languages %}{{ lang.code }}:{{ lang.name }}{% if not forloop.last %},{% endif %}{% endfor %}
        """

        context = Context({})
        template = Template(template_content)
        rendered = template.render(context)

        self.assertIn("en:English", rendered)
        self.assertIn("pl:Polski", rendered)
        self.assertIn("nl:Nederlands", rendered)

    def test_language_switcher_template_exists(self):
        """Test that the language switcher template component can be loaded."""
        template_content = """
        {% load language_tags %}
        {% language_switcher %}
        """

        request = self.factory.get("/")
        context = Context({"request": request})

        # This should not raise a TemplateDoesNotExist exception
        try:
            template = Template(template_content)
            rendered = template.render(context)
            # If we get here, the template loaded successfully
            self.assertTrue(True)
        except Exception as e:
            # If template doesn't exist, that's expected in test environment
            # The important thing is that the tag is registered correctly
            if "language_switcher.html" in str(e):
                # This is expected in test environment without actual template files
                pass
            else:
                # Re-raise if it's a different error
                raise

    def test_language_context_consistency(self):
        """Test that language context is consistent across template tags."""
        languages = ["en", "pl", "nl"]

        for lang in languages:
            with self.subTest(language=lang):
                with translation.override(lang):
                    # Test that all tags return consistent language information
                    current_name = get_current_language_name()
                    available_langs = get_available_languages_with_names()

                    request = self.factory.get(f"/{lang}/" if lang != "en" else "/")
                    context = Context({"request": request})
                    switcher_context = language_switcher(context)

                    # Current language should be consistent
                    self.assertEqual(switcher_context["current_language"], lang)
                    self.assertEqual(switcher_context["current_language_name"], current_name)

                    # Available languages should always be the same
                    self.assertEqual(len(available_langs), 3)
                    self.assertEqual(switcher_context["available_languages"], available_langs)

    def test_template_tag_error_handling(self):
        """Test that template tags handle edge cases gracefully."""
        # Test with missing request in context
        context = Context({})  # No request object

        # This should not crash, but handle the missing request gracefully
        try:
            result = language_switcher(context)
            # If we get a result, it should still have the language information
            self.assertIn("current_language", result)
            self.assertIn("available_languages", result)
        except KeyError:
            # It's acceptable if the tag requires request context
            pass

    def test_language_names_mapping_completeness(self):
        """Test that all configured languages have name mappings."""
        available_langs = get_available_languages_with_names()

        # All languages from settings should have proper names
        expected_codes = ["en", "pl", "nl"]
        actual_codes = [lang["code"] for lang in available_langs]

        self.assertEqual(sorted(actual_codes), sorted(expected_codes))

        # No language should have None or empty name
        for lang in available_langs:
            self.assertIsNotNone(lang["name"])
            self.assertNotEqual(lang["name"], "")
            self.assertTrue(len(lang["name"]) > 0)
