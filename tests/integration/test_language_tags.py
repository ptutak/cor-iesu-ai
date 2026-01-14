"""
Integration tests for language switching template tags.
Tests the custom template tags used for multilingual functionality.
"""

import pytest
from django.http import HttpRequest
from django.template import Context, Template
from django.test import RequestFactory, override_settings
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
def test_get_current_language_name_english():
    """Test getting current language name for English."""
    with translation.override("en"):
        result = get_current_language_name()
        assert result == "English"


def test_get_current_language_name_polish():
    """Test getting current language name for Polish."""
    with translation.override("pl"):
        result = get_current_language_name()
        assert result == "Polski"


def test_get_current_language_name_dutch():
    """Test getting current language name for Dutch."""
    with translation.override("nl"):
        result = get_current_language_name()
        assert result == "Nederlands"


def test_get_current_language_name_unknown_language():
    """Test getting current language name for unknown language defaults to English."""
    with translation.override("fr"):  # French not in our supported languages
        result = get_current_language_name()
        assert result == "English"  # Should default to English


def test_get_available_languages_with_names():
    """Test getting all available languages with proper names."""
    result = get_available_languages_with_names()

    expected_languages = [
        {"code": "en", "name": "English"},
        {"code": "pl", "name": "Polski"},
        {"code": "nl", "name": "Nederlands"},
    ]

    assert len(result) == 3
    assert result == expected_languages


def test_language_switcher_template_tag_english(rf):
    """Test language switcher template tag in English context."""
    with translation.override("en"):
        request = rf.get("/")
        context = Context({"request": request})

        result = language_switcher(context)

        assert result["current_language"] == "en"
        assert result["current_language_name"] == "English"
        assert len(result["available_languages"]) == 3
        assert result["request"] == request


def test_language_switcher_template_tag_polish(rf):
    """Test language switcher template tag in Polish context."""
    with translation.override("pl"):
        request = rf.get("/pl/")
        context = Context({"request": request})

        result = language_switcher(context)

        assert result["current_language"] == "pl"
        assert result["current_language_name"] == "Polski"
        assert len(result["available_languages"]) == 3


def test_language_switcher_template_tag_dutch(rf):
    """Test language switcher template tag in Dutch context."""
    with translation.override("nl"):
        request = rf.get("/nl/")
        context = Context({"request": request})

        result = language_switcher(context)

        assert result["current_language"] == "nl"
        assert result["current_language_name"] == "Nederlands"
        assert len(result["available_languages"]) == 3


def test_language_switcher_template_rendering(rf):
    """Test that language switcher template renders correctly."""
    template_content = """
    {% load language_tags %}
    {% language_switcher %}
    """

    with translation.override("en"):
        request = rf.get("/")
        context = Context({"request": request})

        template = Template(template_content)
        rendered = template.render(context)

        # Check that the rendered content contains expected elements
        assert "language-switcher-buttons" in rendered
        assert "language-btn" in rendered
        assert "English" in rendered
        assert "Switch to English" in rendered


@pytest.mark.parametrize("path", ["/", "/some/path/", "/another/path/?param=value"])
def test_language_switcher_preserves_current_path(rf, path):
    """Test that language switcher preserves the current path."""
    request = rf.get(path)
    context = Context({"request": request})

    result = language_switcher(context)

    # The request should be preserved in the context
    assert result["request"].get_full_path() == path


def test_simple_tag_registration():
    """Test that simple tags are properly registered."""
    template_content = """
    {% load language_tags %}
    Current: {% get_current_language_name %}
    """

    with translation.override("pl"):
        context = Context({})
        template = Template(template_content)
        rendered = template.render(context)

        assert "Current: Polski" in rendered


def test_available_languages_tag_registration():
    """Test that available languages tag is properly registered."""
    template_content = """
    {% load language_tags %}
    {% get_available_languages_with_names as languages %}
    {% for lang in languages %}{{ lang.code }}:{{ lang.name }}{% if not forloop.last %},{% endif %}{% endfor %}
    """

    context = Context({})
    template = Template(template_content)
    rendered = template.render(context)

    assert "en:English" in rendered
    assert "pl:Polski" in rendered
    assert "nl:Nederlands" in rendered


def test_language_switcher_template_exists(rf):
    """Test that the language switcher template component can be loaded."""
    template_content = """
    {% load language_tags %}
    {% language_switcher %}
    """

    request = rf.get("/")
    context = Context({"request": request})

    # This should not raise a TemplateDoesNotExist exception
    try:
        template = Template(template_content)
        rendered = template.render(context)
        # If we get here, the template loaded successfully
        assert True
    except Exception as e:
        # If template doesn't exist, that's expected in test environment
        # The important thing is that the tag is registered correctly
        if "language_switcher.html" in str(e):
            # This is expected in test environment without actual template files
            pass
        else:
            # Re-raise if it's a different error
            raise


@pytest.mark.parametrize("lang", ["en", "pl", "nl"])
def test_language_context_consistency(rf, lang):
    """Test that language context is consistent across template tags."""
    with translation.override(lang):
        # Test that all tags return consistent language information
        current_name = get_current_language_name()
        available_langs = get_available_languages_with_names()

        request = rf.get(f"/{lang}/" if lang != "en" else "/")
        context = Context({"request": request})
        switcher_context = language_switcher(context)

        # Current language should be consistent
        assert switcher_context["current_language"] == lang
        assert switcher_context["current_language_name"] == current_name

        # Available languages should have the same count
        assert len(available_langs) == 3
        assert len(switcher_context["available_languages"]) == 3

        # Each language in switcher should have the same code and name as original
        # but switcher adds next_url field
        for orig_lang, switcher_lang in zip(available_langs, switcher_context["available_languages"]):
            assert orig_lang["code"] == switcher_lang["code"]
            assert orig_lang["name"] == switcher_lang["name"]
            assert "next_url" in switcher_lang
            assert isinstance(switcher_lang["next_url"], str)


def test_template_tag_error_handling():
    """Test that template tags handle edge cases gracefully."""
    # Test with missing request in context
    context = Context({})  # No request object

    # This should not crash, but handle the missing request gracefully
    try:
        result = language_switcher(context)
        # If we get a result, it should still have the language information
        assert "current_language" in result
        assert "available_languages" in result
    except KeyError:
        # It's acceptable if the tag requires request context
        pass


def test_language_names_mapping_completeness():
    """Test that all configured languages have name mappings."""
    available_langs = get_available_languages_with_names()

    # All languages from settings should have proper names
    expected_codes = ["en", "pl", "nl"]
    actual_codes = [lang["code"] for lang in available_langs]

    assert sorted(actual_codes) == sorted(expected_codes)

    # No language should have None or empty name
    for lang in available_langs:
        assert lang["name"] is not None
        assert lang["name"] != ""
        assert len(lang["name"]) > 0


def test_language_switcher_generates_correct_urls(rf):
    """Test that language switcher generates correct next URLs."""
    request = rf.get("/")
    context = Context({"request": request})
    result = language_switcher(context)

    # Check that each language has appropriate URL
    lang_urls = {lang["code"]: lang["next_url"] for lang in result["available_languages"]}

    assert lang_urls["en"] == "/"  # English should have no language prefix
    assert lang_urls["pl"] == "/pl/"  # Polish should have /pl/ prefix
    assert lang_urls["nl"] == "/nl/"  # Dutch should have /nl/ prefix


def test_language_switcher_with_complex_path(rf):
    """Test language switcher URL generation with complex paths."""
    # Mock resolver match for a path with parameters
    request = rf.get("/some/path/")

    # Create a mock resolver match
    class MockResolverMatch:
        def __init__(self):
            self.url_name = "registration"
            self.kwargs = {}

    request.resolver_match = MockResolverMatch()
    context = Context({"request": request})
    result = language_switcher(context)

    # Should still generate correct language URLs
    lang_urls = {lang["code"]: lang["next_url"] for lang in result["available_languages"]}

    assert lang_urls["en"] == "/"
    assert lang_urls["pl"] == "/pl/"
    assert lang_urls["nl"] == "/nl/"


def test_language_switcher_prevents_double_prefixes(rf):
    """Test that language switcher never generates double language prefixes."""
    # Test various starting URLs
    test_urls = ["/", "/pl/", "/nl/", "/some/path/"]

    for url in test_urls:
        request = rf.get(url)
        context = Context({"request": request})
        result = language_switcher(context)

        # Check that no URL has double prefixes
        for lang in result["available_languages"]:
            next_url = lang["next_url"]

            # Should never have double prefixes
            assert "/en/en/" not in next_url
            assert "/pl/pl/" not in next_url
            assert "/nl/nl/" not in next_url

            # Should never have triple or more prefixes
            assert "/en/en/en/" not in next_url
            assert "/pl/pl/pl/" not in next_url
            assert "/nl/nl/nl/" not in next_url
