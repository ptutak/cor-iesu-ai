from collections.abc import Callable
from typing import Any

from django import forms
from django.conf import settings
from django.contrib import admin
from django.db import models as django_models
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString

from .models import (
    Collection,
    CollectionConfig,
    CollectionMaintainer,
    Config,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


def admin_display(
    description: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Set short_description on admin methods.

    Args:
        description: The description text to display in admin interface

    Returns:
        A decorator function that sets the short_description attribute
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.short_description = description  # type: ignore
        return func

    return decorator


class CollectionLanguageWidget(forms.CheckboxSelectMultiple):
    """Custom widget for selecting available languages in Collection admin."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form with dynamic language choices.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.choices = [(code, name) for code, name in settings.LANGUAGES]


class CollectionAdminForm(forms.ModelForm[Collection]):
    """Custom form for Collection admin with language selection."""

    available_languages = forms.MultipleChoiceField(
        choices=[],  # Will be set in __init__
        widget=CollectionLanguageWidget,
        required=True,
        help_text="Select which languages this collection is available in.",
        label="Available Languages",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form with dynamic language choices.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)
        # Set choices dynamically based on settings
        # Type ignore needed for dynamic field assignment
        self.fields["available_languages"].choices = [(code, name) for code, name in settings.LANGUAGES]  # type: ignore

        # Set initial values if editing existing instance
        if self.instance and self.instance.pk and self.instance.available_languages:
            self.fields["available_languages"].initial = self.instance.available_languages

    def clean_available_languages(self) -> list[str]:
        """Validate that selected languages are valid.

        Returns:
            List of validated language codes

        Raises:
            ValidationError: If no languages selected or invalid codes provided
        """
        languages: list[str] = self.cleaned_data.get("available_languages", [])
        if not languages:
            raise forms.ValidationError("At least one language must be selected.")

        valid_codes = {code for code, name in settings.LANGUAGES}
        invalid_codes = set(languages) - valid_codes
        if invalid_codes:
            raise forms.ValidationError(f"Invalid language codes: {', '.join(invalid_codes)}")

        return languages

    class Meta:
        """Form meta configuration."""

        model = Collection
        fields = "__all__"


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin[Period]):
    """Admin configuration for Period model."""

    list_display = ("name", "description")
    search_fields = ("name", "description")
    list_filter = ("name",)

    @admin.action(description="Generate standard hour periods")
    def generate_standard_hour_periods(self, request: HttpRequest, queryset: django_models.QuerySet[Period]) -> None:
        """Generate 24 standard hour periods (00:00-01:00, 01:00-02:00, etc.).

        Args:
            request: The HTTP request object
            queryset: The queryset of selected objects (not used by this action)
        """
        for hour in range(0, 24):
            Period.objects.get_or_create(name=f"{hour:02}:00 - {hour + 1:02}:00")

    actions = ["generate_standard_hour_periods"]


@admin.register(PeriodCollection)
class PeriodCollectionAdmin(admin.ModelAdmin[PeriodCollection]):
    """Admin configuration for PeriodCollection model."""

    list_display = ("collection", "period", "get_assignment_count")
    list_filter = ("collection",)
    search_fields = ("collection__name", "period__name")

    @admin_display("Assignments")
    def get_assignment_count(self, obj: PeriodCollection) -> SafeString:
        """Get count of assignments for this period collection.

        Args:
            obj: The PeriodCollection instance

        Returns:
            SafeString: HTML formatted count display
        """
        count: int = PeriodAssignment.objects.filter(period_collection=obj).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)


@admin.register(Maintainer)
class MaintainerAdmin(admin.ModelAdmin[Maintainer]):
    """Admin configuration for Maintainer model."""

    list_display = ("get_full_name", "user_email", "phone_number", "country")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__username",
        "user__email",
        "phone_number",
        "country",
    )
    list_filter = ("country",)

    @admin_display("Name")
    def get_full_name(self, obj: Maintainer) -> str:
        """Get the full name or username of the maintainer.

        Args:
            obj: The Maintainer instance

        Returns:
            str: Full name or username if full name is empty
        """
        full_name: str = obj.user.get_full_name()
        return full_name or obj.user.username

    @admin_display("Email")
    def user_email(self, obj: Maintainer) -> str:
        """Get the email address of the maintainer.

        Args:
            obj: The Maintainer instance

        Returns:
            str: Email address of the maintainer
        """
        email: str = obj.user.email
        return email


@admin.register(CollectionMaintainer)
class CollectionMaintainerAdmin(admin.ModelAdmin[CollectionMaintainer]):
    """Admin configuration for CollectionMaintainer model."""

    list_display = (
        "collection",
        "get_maintainer_name",
        "get_maintainer_email",
        "get_maintainer_country",
    )
    search_fields = (
        "collection__name",
        "maintainer__user__first_name",
        "maintainer__user__last_name",
        "maintainer__user__username",
        "maintainer__user__email",
        "maintainer__country",
    )
    list_filter = ("collection", "maintainer__country")

    @admin_display("Maintainer Name")
    def get_maintainer_name(self, obj: CollectionMaintainer) -> str:
        """Get the full name or username of the collection maintainer.

        Args:
            obj: The CollectionMaintainer instance

        Returns:
            str: Full name or username if full name is empty
        """
        full_name: str = obj.maintainer.user.get_full_name()
        return full_name or obj.maintainer.user.username

    @admin_display("Email")
    def get_maintainer_email(self, obj: CollectionMaintainer) -> str:
        """Get the email address of the collection maintainer.

        Args:
            obj: The CollectionMaintainer instance

        Returns:
            str: Email address of the maintainer
        """
        email: str = obj.maintainer.user.email
        return email

    @admin_display("Country")
    def get_maintainer_country(self, obj: CollectionMaintainer) -> str:
        """Get the country of the collection maintainer.

        Args:
            obj: The CollectionMaintainer instance

        Returns:
            str: Country of the maintainer
        """
        country: str = obj.maintainer.country
        return country


@admin.register(PeriodAssignment)
class PeriodAssignmentAdmin(admin.ModelAdmin[PeriodAssignment]):
    """Admin configuration for PeriodAssignment model."""

    list_display = ("period_collection", "get_email_status", "deletion_token_short")
    list_filter = ("period_collection__collection", "period_collection__period")
    search_fields = (
        "period_collection__collection__name",
        "period_collection__period__name",
        "deletion_token",
    )
    readonly_fields = ("email_hash", "salt", "deletion_token")

    @admin_display("Email Status")
    def get_email_status(self, obj: PeriodAssignment) -> str:
        """Show that email is hashed for privacy.

        Args:
            obj: The PeriodAssignment instance

        Returns:
            str: Status indicating email is hashed
        """
        return "Hashed for Privacy"

    @admin_display("Token")
    def deletion_token_short(self, obj: PeriodAssignment) -> str:
        """Show shortened deletion token.

        Args:
            obj: The PeriodAssignment instance

        Returns:
            str: Shortened deletion token
        """
        return f"{obj.deletion_token[:8]}..." if obj.deletion_token else ""

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        """Limit change permissions to protect privacy data.

        Args:
            request: The HTTP request object
            obj: The model instance being changed (optional)

        Returns:
            bool: Always False to prevent changes
        """
        return False

    def has_add_permission(self, request: Any) -> bool:
        """Disable adding assignments through admin for privacy.

        Args:
            request: The HTTP request object

        Returns:
            bool: Always False to prevent additions
        """
        return False


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin[Collection]):
    """Admin configuration for Collection model."""

    form = CollectionAdminForm
    list_display = (
        "name",
        "enabled",
        "get_available_languages_display",
        "get_period_count",
        "get_maintainer_count",
    )
    list_filter = ("enabled", "available_languages")
    search_fields = ("name", "description")

    fieldsets = (
        (None, {"fields": ("name", "description", "enabled")}),
        (
            "Languages",
            {
                "fields": ("available_languages",),
                "description": "Select which languages this collection should be available in.",
            },
        ),
    )

    def get_form(
        self,
        request: Any,
        obj: Collection | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[forms.ModelForm[Collection]]:
        """Get the form class and set the model.

        Args:
            request: HTTP request object
            obj: Collection instance being edited
            change: Whether this is a change form
            kwargs: Additional keyword arguments

        Returns:
            Form class for Collection admin
        """
        form_class = super().get_form(request, obj, change=change, **kwargs)
        return form_class

    @admin_display("Available Languages")
    def get_available_languages_display(self, obj: Collection) -> str:
        """Display available languages as flags and names.

        Args:
            obj: The Collection instance

        Returns:
            str: Formatted display of available languages
        """
        if not obj.available_languages:
            return "None"

        language_names = dict(settings.LANGUAGES)
        flags = {"en": "🇺🇸", "pl": "🇵🇱", "nl": "🇳🇱"}

        display_items = []
        for code in obj.available_languages:
            flag = flags.get(code, "🌐")
            name = language_names.get(code, code.upper())
            display_items.append(f"{flag} {name}")

        return " | ".join(display_items)

    @admin_display("Periods")
    def get_period_count(self, obj: Collection) -> int:
        """Get count of periods in this collection.

        Args:
            obj: The Collection instance

        Returns:
            int: Number of periods in collection
        """
        return obj.periods.count()

    @admin_display("Maintainers")
    def get_maintainer_count(self, obj: Collection) -> int:
        """Get count of maintainers for this collection.

        Args:
            obj: The Collection instance

        Returns:
            int: Number of maintainers for collection
        """
        return CollectionMaintainer.objects.filter(collection=obj).count()


admin.site.register(Config)
admin.site.register(CollectionConfig)
