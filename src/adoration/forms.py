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


class PeriodAssignmentForm(forms.ModelForm[PeriodAssignment]):
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

    class Meta:
        """Meta configuration for PeriodAssignmentForm."""

        model = PeriodAssignment
        fields = [
            "attendant_name",
            "attendant_email",
            "attendant_phone_number",
            "period_collection",
        ]
        labels = {
            "attendant_name": "Full Name *",
            "attendant_email": "Email Address *",
            "attendant_phone_number": "Phone Number (optional)",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with dynamic period queryset based on collection.

        Args:
            args: Positional arguments including form data and files
            kwargs: Keyword arguments including instance and initial data
        """
        super().__init__(*args, **kwargs)
        self.fields["attendant_phone_number"].required = False

        # Set up dynamic period queryset based on collection
        if "collection" in self.data:
            try:
                collection_data = self.data.get("collection")
                if collection_data is not None:
                    collection_id = int(collection_data)
                    period_field = cast(
                        forms.ModelChoiceField[PeriodCollection],
                        self.fields["period_collection"],
                    )
                    period_field.queryset = PeriodCollection.objects.filter(collection_id=collection_id).select_related(
                        "period", "collection"
                    )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            period_field = cast(
                forms.ModelChoiceField[PeriodCollection],
                self.fields["period_collection"],
            )
            period_field.queryset = PeriodCollection.objects.filter(
                collection=self.instance.period_collection.collection
            ).select_related("period", "collection")

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

        # Check if user is already assigned to this period
        if period_collection and attendant_email:
            existing_assignment: bool = PeriodAssignment.objects.filter(
                period_collection=period_collection, attendant_email=attendant_email
            ).exists()

            if existing_assignment:
                raise ValidationError("You are already registered for this period.")

        return cleaned_data

    def save(self, commit: bool = True) -> PeriodAssignment:
        """Save the period assignment instance.

        Args:
            commit: Whether to save the instance to database immediately

        Returns:
            PeriodAssignment: The saved assignment instance
        """
        instance = super().save(commit=False)

        if commit:
            instance.save()
        return instance
