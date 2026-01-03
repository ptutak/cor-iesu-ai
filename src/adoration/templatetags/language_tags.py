from django import template
from django.conf import settings
from django.utils import translation

register = template.Library()


@register.simple_tag
def get_current_language_name():
    """Get the current language display name."""
    current_lang = translation.get_language()

    language_names = {
        "en": "English",
        "pl": "Polski",
        "nl": "Nederlands",
    }

    return language_names.get(current_lang, "English")


@register.simple_tag
def get_available_languages_with_names():
    """Get available languages with display names."""
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
def language_switcher(context):
    """Render language switcher component."""
    current_lang = translation.get_language()
    available_languages = get_available_languages_with_names()
    current_lang_name = get_current_language_name()

    return {
        "current_language": current_lang,
        "current_language_name": current_lang_name,
        "available_languages": available_languages,
        "request": context["request"],
    }
