from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError

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
        empty_label="Select a collection",
        required=True,
    )

    period_collection = forms.ModelChoiceField(
        queryset=PeriodCollection.objects.select_related("collection", "period").filter(collection__enabled=True),
        empty_label="Select a period",
    )

    attendant_name = forms.CharField(
        max_length=100,
        label="Full Name *",
        required=True,
    )

    attendant_email = forms.EmailField(
        max_length=80,
        label="Email Address *",
        required=True,
    )

    attendant_phone_number = forms.CharField(
        max_length=15,
        label="Phone Number (optional)",
        required=False,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with dynamic period queryset based on collection.

        Args:
            args: Positional arguments including form data and files
            kwargs: Keyword arguments including instance and initial data
        """
        super().__init__(*args, **kwargs)

        # Filter collections to only show those with maintainers
        from .models import CollectionMaintainer

        collections_with_maintainers = Collection.objects.filter(
            enabled=True,
            id__in=CollectionMaintainer.objects.values_list("collection_id", flat=True),
        )
        collection_field = self.fields["collection"]
        if isinstance(collection_field, forms.ModelChoiceField):
            collection_field.queryset = collections_with_maintainers

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
            raise ValidationError("Please select a period.")

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
            raise ValidationError(f"This period is full. Maximum {collection_limit} assignments allowed.")

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
                    raise ValidationError("You are already registered for this period.")

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
        label="Email Address *",
        help_text="Enter the email address used for registration to confirm deletion.",
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
            raise ValidationError("Email address does not match the registration.")
        return email or ""
