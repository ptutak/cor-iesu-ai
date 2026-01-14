from typing import Any

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils import translation

register = template.Library()


@register.simple_tag
def get_current_language_name() -> str:
    """Get the current language display name.

    Returns:
        Display name of the current language
    """
    current_lang = translation.get_language()

    language_names = {
        "en": "English",
        "pl": "Polski",
        "nl": "Nederlands",
    }

    return language_names.get(current_lang, "English")


@register.simple_tag
def get_available_languages_with_names() -> list[dict[str, str]]:
    """Get available languages with display names.

    Returns:
        List of dictionaries containing language code and name
    """
    languages = []

    language_names = {
        "en": "English",
        "pl": "Polski",
        "nl": "Nederlands",
    }

    for lang_code, lang_name in settings.LANGUAGES:
        languages.append({"code": lang_code, "name": language_names.get(lang_code, lang_name)})

    return languages


@register.inclusion_tag("adoration/language_switcher.html", takes_context=True)
def language_switcher(context: dict[str, Any]) -> dict[str, Any]:
    """Render language switcher component.

    Args:
        context: Template context containing request and other variables

    Returns:
        Dictionary with language switcher data for template rendering
    """
    current_lang = translation.get_language()
    available_languages = get_available_languages_with_names()
    current_lang_name = get_current_language_name()

    request = context["request"]

    # Create a copy of available_languages with next_url added
    languages_with_urls = []
    for language in available_languages:
        lang_code = language["code"]
        language_copy = language.copy()

        # Use reverse() with language override to generate proper URLs
        if hasattr(request, "resolver_match") and request.resolver_match:
            url_name = request.resolver_match.url_name
            kwargs = request.resolver_match.kwargs

            try:
                # Handle English as special case to avoid language prefix
                if lang_code == "en":
                    # For English, temporarily activate English and generate URL
                    with translation.override("en"):
                        if kwargs:
                            # For URLs with parameters (like delete_assignment with token)
                            next_url = reverse(url_name, kwargs=kwargs)
                        else:
                            # For URLs without parameters (like registration)
                            next_url = reverse(url_name)

                    # Remove any language prefix that might have been added
                    if next_url.startswith("/en/"):
                        next_url = next_url[3:]
                    elif next_url.startswith("/pl/") or next_url.startswith("/nl/"):
                        next_url = next_url[3:]

                    # Ensure it starts with /
                    if not next_url.startswith("/"):
                        next_url = "/" + next_url
                else:
                    # Use translation override to get the URL for non-English languages
                    with translation.override(lang_code):
                        if kwargs:
                            # For URLs with parameters (like delete_assignment with token)
                            next_url = reverse(url_name, kwargs=kwargs)
                        else:
                            # For URLs without parameters (like registration)
                            next_url = reverse(url_name)

                language_copy["next_url"] = next_url
            except Exception:
                # Final fallback
                if lang_code == "en":
                    language_copy["next_url"] = "/"
                else:
                    language_copy["next_url"] = f"/{lang_code}/"
        else:
            # Fallback for cases where resolver_match is not available
            if lang_code == "en":
                language_copy["next_url"] = "/"
            else:
                language_copy["next_url"] = f"/{lang_code}/"

        languages_with_urls.append(language_copy)

    return {
        "current_language": current_lang,
        "current_language_name": current_lang_name,
        "available_languages": languages_with_urls,
        "request": request,
    }
