from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db import models
from django.http import HttpRequest

# Register your models here.
from .models import (
    Collection,
    CollectionConfig,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


@admin.action(description="Generate standard hour periods")
def generate_standard_hour_periods(
    modeladmin: ModelAdmin, request: HttpRequest, queryset: models.QuerySet
) -> None:
    for hour in range(0, 24):
        Period.objects.get_or_create(name=f"{hour:02}:00 - {hour + 1:02}:00")


class PeriodAdmin(admin.ModelAdmin):
    actions = [generate_standard_hour_periods]


admin.site.register(
    [Collection, CollectionConfig, Period, PeriodAssignment, PeriodCollection],
    PeriodAdmin,
)
