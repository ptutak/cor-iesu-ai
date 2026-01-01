from typing import Any, Dict, Optional

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Collection,
    CollectionConfig,
    Config,
    PeriodAssignment,
    PeriodCollection,
)


class PeriodAssignmentForm(forms.ModelForm):
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.filter(enabled=True),
        empty_label="Select a collection",
        required=True,
    )

    period_collection = forms.ModelChoiceField(
        queryset=PeriodCollection.objects.select_related("collection", "period").filter(
            collection__enabled=True
        ),
        empty_label="Select a period",
    )

    class Meta:
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
        super().__init__(*args, **kwargs)
        self.fields["attendant_phone_number"].required = False

        # Set up dynamic period queryset based on collection
        if "collection" in self.data:
            try:
                collection_data = self.data.get("collection")
                if collection_data is not None:
                    collection_id = int(collection_data)
                    self.fields[
                        "period_collection"
                    ].queryset = PeriodCollection.objects.filter(  # type: ignore[misc]
                        collection_id=collection_id
                    ).select_related("period", "collection")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields["period_collection"].queryset = PeriodCollection.objects.filter(  # type: ignore[misc]
                collection=self.instance.period_collection.collection
            ).select_related("period", "collection")

    def clean_period_collection(self) -> Optional[PeriodCollection]:
        period_collection = self.cleaned_data.get("period_collection")
        if not period_collection:
            raise ValidationError("Please select a period.")

        # Check assignment limits
        collection = period_collection.collection
        current_assignments = PeriodAssignment.objects.filter(
            period_collection=period_collection
        ).count()

        # Check collection-specific limit first
        collection_limit: Optional[int] = None
        try:
            collection_config = CollectionConfig.objects.get(
                collection=collection, name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT
            )
            collection_limit = int(collection_config.value)
        except (CollectionConfig.DoesNotExist, ValueError):
            # Fall back to default limit
            try:
                default_config = Config.objects.get(
                    name=Config.DefaultValues.ASSIGNMENT_LIMIT
                )
                collection_limit = int(default_config.value)
            except (Config.DoesNotExist, ValueError):
                pass

        if collection_limit is not None and current_assignments >= collection_limit:
            raise ValidationError(
                f"This period is full. Maximum {collection_limit} assignments allowed."
            )

        return period_collection

    def clean(self) -> Optional[Dict[str, Any]]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        period_collection = cleaned_data.get("period_collection")
        attendant_email = cleaned_data.get("attendant_email")

        # Check if user is already assigned to this period
        if period_collection and attendant_email:
            existing_assignment = PeriodAssignment.objects.filter(
                period_collection=period_collection, attendant_email=attendant_email
            ).exists()

            if existing_assignment:
                raise ValidationError("You are already registered for this period.")

        return cleaned_data

    def save(self, commit: bool = True) -> PeriodAssignment:
        instance = super().save(commit=False)

        if commit:
            instance.save()
        return instance
