from django.contrib import admin
from django.utils.html import format_html

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


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    list_filter = ("name",)


@admin.register(PeriodCollection)
class PeriodCollectionAdmin(admin.ModelAdmin):
    list_display = ("collection", "period", "get_assignment_count")
    list_filter = ("collection",)
    search_fields = ("collection__name", "period__name")

    def get_assignment_count(self, obj):
        count = PeriodAssignment.objects.filter(period_collection=obj).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)

    get_assignment_count.short_description = "Assignments"  # type: ignore[misc]


@admin.register(Maintainer)
class MaintainerAdmin(admin.ModelAdmin):
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

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    get_full_name.short_description = "Name"  # type: ignore[misc]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"  # type: ignore[misc]


@admin.register(CollectionMaintainer)
class CollectionMaintainerAdmin(admin.ModelAdmin):
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

    def get_maintainer_name(self, obj):
        return obj.maintainer.user.get_full_name() or obj.maintainer.user.username

    get_maintainer_name.short_description = "Maintainer Name"  # type: ignore[misc]

    def get_maintainer_email(self, obj):
        return obj.maintainer.user.email

    get_maintainer_email.short_description = "Email"  # type: ignore[misc]

    def get_maintainer_country(self, obj):
        return obj.maintainer.country

    get_maintainer_country.short_description = "Country"  # type: ignore[misc]


admin.site.register(Config)
admin.site.register(Collection)
admin.site.register(CollectionConfig)
admin.site.register(PeriodAssignment)
