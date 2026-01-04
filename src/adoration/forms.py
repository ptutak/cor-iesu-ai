from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from .models import (
    Collection,
    CollectionConfig,
    Config,
    PeriodAssignment,
    PeriodCollection,
)


class PeriodAssignmentForm(forms.Form):
    """Form for period assignment registration."""

    collection = forms.ModelChoiceField(
        queryset=Collection.objects.filter(enabled=True),
        empty_label=_("Select a collection"),
        required=True,
        label=_("Collection"),
    )

    period_collection = forms.ModelChoiceField(
        queryset=PeriodCollection.objects.select_related("collection", "period").filter(collection__enabled=True),
        empty_label=_("Select a period"),
        label=_("Period"),
    )

    attendant_name = forms.CharField(
        max_length=100,
        label=_("Full Name *"),
        required=True,
    )

    attendant_email = forms.EmailField(
        max_length=80,
        label=_("Email Address *"),
        required=True,
    )

    attendant_phone_number = forms.CharField(
        max_length=15,
        label=_("Phone Number (optional)"),
        required=False,
    )

    privacy_accepted = forms.BooleanField(
        required=True,
        label=_("Privacy Agreement"),
        help_text=_(
            "I acknowledge that my email address will be sent directly to the collection "
            "maintainer(s) for coordination purposes. I understand that no personal data "
            "is stored in the system database - only a secure hash for verification. "
            "I consent to receiving confirmation and coordination emails related to my registration."
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with dynamic period queryset based on collection.

        Args:
            args: Positional arguments including form data and files
            kwargs: Keyword arguments including instance and initial data
        """
        super().__init__(*args, **kwargs)

        # Get current language
        current_language = translation.get_language() or "en"

        # Filter collections to only show those with maintainers who have email addresses
        # AND are available in the current language
        from .models import CollectionMaintainer

        # Get collections that have at least one maintainer with a non-empty email
        # and are available in the current language
        # First get all enabled collections with valid maintainers
        collections_with_maintainers = Collection.objects.filter(
            enabled=True,
            id__in=CollectionMaintainer.objects.filter(maintainer__user__email__isnull=False)
            .exclude(maintainer__user__email="")
            .exclude(maintainer__user__email__regex=r"^\s*$")  # Exclude whitespace-only
            .values_list("collection_id", flat=True),
        )

        # Filter by language using Python (SQLite compatible)
        available_collection_ids = [
            collection.pk
            for collection in collections_with_maintainers
            if collection.is_available_in_language(current_language)
        ]

        collections_with_valid_maintainers = Collection.objects.filter(id__in=available_collection_ids)
        collection_field = self.fields["collection"]
        if isinstance(collection_field, forms.ModelChoiceField):
            collection_field.queryset = collections_with_valid_maintainers

        # Set up dynamic period queryset based on collection
        if "collection" in self.data:
            try:
                collection_data = self.data.get("collection")
                if collection_data is not None:
                    collection_id = int(collection_data)
                    period_field = self.fields["period_collection"]
                    if isinstance(period_field, forms.ModelChoiceField):
                        period_field.queryset = PeriodCollection.objects.filter(
                            collection_id=collection_id
                        ).select_related("period", "collection")
            except (ValueError, TypeError):
                pass

    def clean_period_collection(self) -> PeriodCollection | None:
        """Validate period collection selection and check assignment limits.

        Returns:
            PeriodCollection: The validated period collection

        Raises:
            ValidationError: If no period is selected or period is full
        """
        period_collection = cast(PeriodCollection | None, self.cleaned_data.get("period_collection"))
        if not period_collection:
            raise ValidationError(_("Please select a period."))

        # Check assignment limits
        collection = period_collection.collection
        current_assignments: int = PeriodAssignment.objects.filter(period_collection=period_collection).count()

        # Check collection-specific limit first
        collection_limit: int | None = None
        try:
            collection_config = CollectionConfig.objects.get(
                collection=collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
            )
            collection_limit = int(collection_config.value)
        except (CollectionConfig.DoesNotExist, ValueError):
            # Fall back to default limit
            try:
                default_config = Config.objects.get(name=Config.DefaultValues.ASSIGNMENT_LIMIT)
                collection_limit = int(default_config.value)
            except (Config.DoesNotExist, ValueError):
                pass

        if collection_limit is not None and current_assignments >= collection_limit:
            raise ValidationError(
                _("This period is full. Maximum %(limit)s assignments allowed.") % {"limit": collection_limit}
            )

        return period_collection

    def clean(self) -> dict[str, Any] | None:
        """Validate form data and check for duplicate registrations.

        Returns:
            dict[str, Any]: The cleaned form data

        Raises:
            ValidationError: If user is already registered for the period
        """
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        period_collection = cleaned_data.get("period_collection")
        attendant_email = cleaned_data.get("attendant_email")

        # Check if user is already assigned to this period by checking all assignments
        if period_collection and attendant_email:
            # Get all assignments for this period and check if any match the email
            existing_assignments = PeriodAssignment.objects.filter(period_collection=period_collection)
            for assignment in existing_assignments:
                if assignment.verify_email(attendant_email):
                    raise ValidationError(_("You are already registered for this period."))

        return cleaned_data

    def save(self, commit: bool = True) -> PeriodAssignment:
        """Save the period assignment instance using hashed email.

        Args:
            commit: Whether to save the instance to database immediately

        Returns:
            PeriodAssignment: The saved assignment instance
        """
        period_collection = self.cleaned_data["period_collection"]
        attendant_email = self.cleaned_data["attendant_email"]

        instance = PeriodAssignment.create_with_email(
            email=attendant_email,
            period_collection=period_collection,
        )

        if commit:
            instance.save()
        return instance


class DeletionConfirmForm(forms.Form):
    """Form for confirming assignment deletion with email verification."""

    email = forms.EmailField(
        label=_("Email Address *"),
        help_text=_("Enter the email address used for registration to confirm deletion."),
        required=True,
    )

    def __init__(self, assignment: PeriodAssignment, *args: Any, **kwargs: Any) -> None:
        """Initialize form with assignment reference.

        Args:
            assignment: The assignment to be deleted
            args: Positional arguments
            kwargs: Keyword arguments
        """
        self.assignment = assignment
        super().__init__(*args, **kwargs)

    def clean_email(self) -> str:
        """Validate that the provided email matches the assignment.

        Returns:
            str: The validated email address

        Raises:
            ValidationError: If email doesn't match the assignment
        """
        email = self.cleaned_data.get("email")
        if email and not self.assignment.verify_email(email):
            raise ValidationError(_("Email address does not match the registration."))
        return email or ""


class CollectionForm(forms.ModelForm[Collection]):
    """Form for creating and updating collections in maintainer views."""

    available_languages = forms.MultipleChoiceField(
        choices=[],  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text=_("Select which languages this collection is available in."),
        label=_("Available Languages"),
    )

    class Meta:
        model = Collection
        fields = ["name", "description", "enabled", "available_languages"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Enter collection name"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Enter collection description (optional)"),
                }
            ),
            "enabled": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form with dynamic language choices.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)

        # Set language choices from Django settings
        from django.conf import settings

        self.fields["available_languages"].choices = settings.LANGUAGES

        # Set initial value for existing instances
        if self.instance and self.instance.pk and self.instance.available_languages:
            self.fields["available_languages"].initial = self.instance.available_languages

    def clean_available_languages(self) -> list[str]:
        """Validate available languages selection.

        Returns:
            list[str]: List of valid language codes

        Raises:
            ValidationError: If no languages selected or invalid codes provided
        """
        languages = self.cleaned_data.get("available_languages", [])

        if not languages:
            raise ValidationError(_("Collection must have at least one available language."))

        # Validate that all selected languages are in Django settings
        from django.conf import settings

        valid_language_codes = {code for code, name in settings.LANGUAGES}
        invalid_codes = set(languages) - valid_language_codes

        if invalid_codes:
            raise ValidationError(
                f"Invalid language codes: {', '.join(sorted(invalid_codes))}. "
                f"Valid codes are: {', '.join(sorted(valid_language_codes))}"
            )

        return languages

    def save(self, commit: bool = True) -> Collection:
        """Save the collection with proper language handling.

        Args:
            commit: Whether to save to database immediately

        Returns:
            Collection: The saved collection instance
        """
        collection = super().save(commit=False)

        # Ensure available_languages is properly set as a list
        if "available_languages" in self.cleaned_data:
            collection.available_languages = self.cleaned_data["available_languages"]

        if commit:
            collection.save()

        return collection
