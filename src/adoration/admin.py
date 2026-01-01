from collections.abc import Callable
from typing import Any

from django.contrib import admin
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


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin[Period]):
    """Admin configuration for Period model."""

    list_display = ("name", "description")
    search_fields = ("name", "description")
    list_filter = ("name",)


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


admin.site.register(Config)
admin.site.register(Collection)
admin.site.register(CollectionConfig)
admin.site.register(PeriodAssignment)
