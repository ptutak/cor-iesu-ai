import hashlib
import secrets
from typing import TYPE_CHECKING, Any

from django.contrib.auth.models import User
from django.db import models

if TYPE_CHECKING:
    pass

# Create your models here.


class Config(models.Model):
    """Configuration model for storing application settings."""

    # db_table = "config"

    objects: models.Manager["Config"]

    class DefaultValues(models.TextChoices):
        """Default configuration keys available in the system."""

        ASSIGNMENT_LIMIT = "ASSIGNMENT_LIMIT"
        EMAIL_HOST = "EMAIL_HOST"
        EMAIL_PORT = "EMAIL_PORT"
        EMAIL_USE_TLS = "EMAIL_USE_TLS"
        EMAIL_USE_SSL = "EMAIL_USE_SSL"
        EMAIL_HOST_USER = "EMAIL_HOST_USER"
        EMAIL_HOST_PASSWORD = "EMAIL_HOST_PASSWORD"
        DEFAULT_FROM_EMAIL = "DEFAULT_FROM_EMAIL"

    name = models.CharField(max_length=100, unique=True, blank=False)
    value = models.CharField(max_length=255, blank=False)
    description = models.CharField(max_length=600, blank=False)


class Period(models.Model):
    """Model representing time periods for adoration scheduling."""

    # db_table = "periods"

    objects: models.Manager["Period"]

    name = models.CharField(max_length=100, unique=True, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Collection(models.Model):
    """Model representing a collection of periods for adoration."""

    # db_table = "collections"

    objects: models.Manager["Collection"]

    name = models.CharField(max_length=100, unique=True, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)
    enabled = models.BooleanField(blank=False, default=True)
    periods = models.ManyToManyField(Period, through="PeriodCollection")  # type: ignore

    def __str__(self) -> str:
        return self.name


class PeriodCollection(models.Model):
    """Junction model linking periods to collections."""

    # db_table = "period_collections"

    objects: models.Manager["PeriodCollection"]

    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    class Meta:
        """Meta configuration for PeriodCollection model."""

        constraints = [
            models.UniqueConstraint(
                fields=["period", "collection"],
                name="period_collection_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection}: {self.period}"


class CollectionConfig(models.Model):
    """Configuration settings specific to individual collections."""

    # db_table = "collection_configs"

    objects: models.Manager["CollectionConfig"]

    class ConfigKeys(models.TextChoices):
        """Available configuration keys for collections."""

        ASSIGNMENT_LIMIT = "ASSIGNMENT_LIMIT"

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=False, choices=ConfigKeys)
    value = models.CharField(max_length=255, blank=False)
    description = models.CharField(max_length=600, blank=True, null=True)

    class Meta:
        """Meta configuration for CollectionConfig model."""

        constraints = [
            models.UniqueConstraint(
                fields=["collection", "name"],
                name="collection_config_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection}: {self.name}"


class PeriodAssignment(models.Model):
    """Model representing a person's assignment to a specific period."""

    # db_table = "period_assignments"

    objects: models.Manager["PeriodAssignment"]

    period_collection = models.ForeignKey(PeriodCollection, on_delete=models.CASCADE)
    attendant_name = models.CharField(max_length=100, blank=False)
    attendant_email = models.CharField(max_length=80, blank=False, null=False)
    attendant_phone_number = models.CharField(max_length=15, blank=True, null=True)
    deletion_token = models.CharField(max_length=128, unique=True, blank=True, null=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the assignment and generate deletion token if needed.

        Args:
            args: Positional arguments including force_insert, force_update, using, update_fields
            kwargs: Keyword arguments for controlling save behavior and database options
        """
        if not self.deletion_token:
            self.deletion_token = self.generate_deletion_token()
        super().save(*args, **kwargs)

    def generate_deletion_token(self) -> str:
        """Generate a secure, hard-to-break token for assignment deletion.

        Returns:
            A secure hash token for assignment deletion
        """
        # Generate a 64-character random token using secrets module
        random_token = secrets.token_urlsafe(48)  # 48 bytes = 64 base64url chars

        # Add additional entropy by including assignment-specific data
        entropy_data = f"{self.attendant_email}{self.attendant_name}"

        # Create a hash of the combined data for extra security
        combined = f"{random_token}{entropy_data}"
        token_hash = hashlib.sha256(combined.encode()).hexdigest()

        return token_hash

    def __str__(self) -> str:
        return f"{self.period_collection.collection.name}: {self.period_collection.period.name} - {self.attendant_name}"


class Maintainer(models.Model):
    """Model representing a maintainer who can manage collections."""

    objects: models.Manager["Maintainer"]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=30, blank=False)

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} ({self.user.email})"


class CollectionMaintainer(models.Model):
    """Junction model linking maintainers to collections they manage."""

    objects: models.Manager["CollectionMaintainer"]

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    maintainer = models.ForeignKey(Maintainer, on_delete=models.CASCADE)

    class Meta:
        """Meta configuration for CollectionMaintainer model."""

        constraints = [
            models.UniqueConstraint(
                fields=["collection", "maintainer"],
                name="collection_maintainer_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.collection.name} - {self.maintainer.user.email}"
