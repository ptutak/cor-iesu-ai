import hashlib
import secrets
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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

    name = models.CharField(max_length=100, unique=True, blank=False, choices=DefaultValues)
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
    available_languages = models.JSONField(
        default=list,
        blank=False,
        help_text="List of language codes this collection is available in (e.g., ['en', 'pl', 'nl'])",
    )
    periods = models.ManyToManyField(Period, through="PeriodCollection")  # type: ignore

    def clean(self) -> None:
        """Validate collection data including maintainers and languages.

        Raises:
            ValidationError: If collection is enabled but has no maintainers or invalid languages
        """
        super().clean()

        # Validate available_languages
        self._validate_available_languages()

        if self.enabled and hasattr(self, "pk") and self.pk:
            # Only check for existing collections (with pk)
            # Check if collection has maintainers using reverse foreign key lookup
            if not hasattr(self, "_maintainers_checked"):
                # Use string reference to avoid import issues
                CollectionMaintainer = self.__class__._meta.apps.get_model("adoration", "CollectionMaintainer")
                if not CollectionMaintainer.objects.filter(collection=self).exists():
                    raise ValidationError("Collection must have at least one maintainer to be enabled.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the collection after validation.

        Args:
            args: Positional arguments for save method
            kwargs: Keyword arguments for save method
        """
        # Set default languages if not specified
        if not self.available_languages:
            self.available_languages = self._get_default_languages()

        self.full_clean()
        super().save(*args, **kwargs)

    def _validate_available_languages(self) -> None:
        """Validate that all language codes in available_languages are valid.

        Raises:
            ValidationError: If any language code is invalid
        """
        if not self.available_languages:
            raise ValidationError("Collection must have at least one available language.")

        if not isinstance(self.available_languages, list):
            raise ValidationError("Available languages must be a list.")

        valid_language_codes = {code for code, name in settings.LANGUAGES}
        invalid_codes = set(self.available_languages) - valid_language_codes

        if invalid_codes:
            raise ValidationError(
                f"Invalid language codes: {', '.join(sorted(invalid_codes))}. "
                f"Valid codes are: {', '.join(sorted(valid_language_codes))}"
            )

    def _get_default_languages(self) -> list[str]:
        """Get default list of available language codes.

        Returns:
            List of all configured language codes
        """
        return [code for code, name in settings.LANGUAGES]

    def is_available_in_language(self, language_code: str) -> bool:
        """Check if collection is available in the specified language.

        Args:
            language_code: Language code to check (e.g., 'en', 'pl', 'nl')

        Returns:
            True if collection is available in the language, False otherwise
        """
        return language_code in (self.available_languages or [])

    def get_available_language_names(self) -> list[tuple[str, str]]:
        """Get list of available languages as (code, name) tuples.

        Returns:
            List of (language_code, language_name) tuples for available languages
        """
        if not self.available_languages:
            return []

        language_dict = dict(settings.LANGUAGES)
        return [(code, language_dict.get(code, code)) for code in self.available_languages if code in language_dict]

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
    email_hash = models.CharField(max_length=128, blank=False, null=False)
    salt = models.CharField(max_length=32, blank=False, null=False)
    deletion_token = models.CharField(max_length=128, unique=True, blank=False, null=False)
    iterations = models.IntegerField(
        default=320000,
        help_text="Number of PBKDF2 iterations used for email hashing",
    )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the assignment and generate deletion token if needed.

        Args:
            args: Positional arguments including force_insert, force_update, using, update_fields
            kwargs: Keyword arguments for controlling save behavior and database options
        """
        if not self.deletion_token:
            self.deletion_token = self.generate_deletion_token()
        if not self.salt:
            self.salt = secrets.token_hex(16)  # 32 character hex string
        super().save(*args, **kwargs)

    @classmethod
    def generate_deletion_token(cls) -> str:
        """Generate a secure, hard-to-break token for assignment deletion.

        Returns:
            A secure hash token for assignment deletion
        """
        # Generate a 64-character random token using secrets module
        random_token = secrets.token_urlsafe(48)  # 48 bytes = 64 base64url chars

        # Create a hash of the combined data for extra security
        token_hash = hashlib.sha256(random_token.encode()).hexdigest()

        return token_hash

    @classmethod
    def create_with_email(
        cls, email: str, period_collection: Any, deletion_token: str | None = None
    ) -> "PeriodAssignment":
        """Create a new assignment with hashed email.

        Args:
            email: The plain text email address
            period_collection: The period collection for this assignment
            deletion_token: Optional deletion token, will be generated if not provided

        Returns:
            PeriodAssignment: The new assignment instance
        """
        salt = secrets.token_hex(16)  # 32 character hex string
        iterations = 320000  # Default PBKDF2 iterations

        # Generate deletion token if not provided
        if not deletion_token:
            deletion_token = cls.generate_deletion_token()

        # Use PBKDF2 hasher for email hashing with salt and deletion token
        hasher = PBKDF2PasswordHasher()
        combined_data = f"{email}{deletion_token}"
        email_hash = hasher.encode(password=combined_data, salt=salt, iterations=iterations)

        assignment = cls(
            period_collection=period_collection,
            email_hash=email_hash,
            salt=salt,
            deletion_token=deletion_token,
            iterations=iterations,
        )

        return assignment

    def verify_email(self, email: str) -> bool:
        """Verify if the provided email matches the stored hash.

        Args:
            email: The plain text email to verify

        Returns:
            bool: True if email matches, False otherwise
        """
        hasher = PBKDF2PasswordHasher()
        combined_data = f"{email}{self.deletion_token}"
        return hasher.verify(password=combined_data, encoded=self.email_hash)

    def __str__(self) -> str:
        return f"{self.period_collection.collection.name}: {self.period_collection.period.name} - [Hashed Email]"


class Maintainer(models.Model):
    """Model representing a maintainer who can manage collections."""

    objects: models.Manager["Maintainer"]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=30, blank=False)
    periods = models.ManyToManyField(Period, through="MaintainerPeriod")  # type: ignore

    def clean(self) -> None:
        """Validate that the user has an email address.

        Raises:
            ValidationError: If user does not have an email address
        """
        super().clean()
        if not self.user.email or not self.user.email.strip():
            from django.core.exceptions import ValidationError

            raise ValidationError("Maintainer user must have an email address.")

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the maintainer after validation.

        Args:
            args: Positional arguments for save method
            kwargs: Keyword arguments for save method
        """
        self.full_clean()
        super().save(*args, **kwargs)

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


class MaintainerPeriod(models.Model):
    """Junction model linking maintainers to periods they can manage."""

    objects: models.Manager["MaintainerPeriod"]

    maintainer = models.ForeignKey(Maintainer, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta configuration for MaintainerPeriod model."""

        constraints = [
            models.UniqueConstraint(
                fields=["maintainer", "period"],
                name="maintainer_period_unique_constraint",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.maintainer.user.email} - {self.period.name}"
