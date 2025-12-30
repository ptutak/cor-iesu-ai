from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpRequest

# Create your models here.


class Config(models.Model):
    # db_table = "config"

    name = models.CharField(max_length=100, unique=True, blank=False)
    value = models.CharField(max_length=255, blank=False)
    description = models.CharField(max_length=600, blank=False)


class Period(models.Model):
    # db_table = "periods"

    name = models.CharField(max_length=100, unique=True, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Collection(models.Model):
    # db_table = "collections"

    name = models.CharField(max_length=100, unique=True, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)
    enabled = models.BooleanField(blank=False, default=True)
    periods = models.ManyToManyField(Period, through="PeriodCollection")  # type: ignore

    def __str__(self) -> str:
        return self.name


class PeriodCollection(models.Model):
    # db_table = "period_collections"

    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period", "collection"],
                name="period_collection_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection}: {self.period}"


class CollectionConfig(models.Model):
    # db_table = "collection_configs"

    class ConfigKeys(models.TextChoices):
        ASSIGNMENT_LIMIT = "ASSIGNMENT_LIMIT"

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False, choices=ConfigKeys)  # type: ignore
    value = models.CharField(max_length=255, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "name"],
                name="collection_config_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection}: {self.name}"


class PeriodAssignment(models.Model):
    # db_table = "period_assignments"

    period_collection = models.ForeignKey(PeriodCollection, on_delete=models.CASCADE)
    attendant_name = models.CharField(max_length=100, blank=False)
    attendant_email = models.CharField(max_length=80, blank=False)
    attendant_phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.period_collection.collection.name}: {self.period_collection.period.name} - {self.attendant_name}"


class Maintainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=30, blank=False)
