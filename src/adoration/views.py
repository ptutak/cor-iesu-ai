from typing import Any

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from .forms import DeletionConfirmForm, PeriodAssignmentForm
from .models import (
    Collection,
    CollectionMaintainer,
    Config,
    PeriodAssignment,
    PeriodCollection,
)


def registration_view(request: HttpRequest) -> HttpResponse:
    """Handle period assignment registration form submission and display.

    Args:
        request: HTTP request object containing form data

    Returns:
        HttpResponse: Rendered registration form or redirect after successful submission
    """
    if request.method == "POST":
        form = PeriodAssignmentForm(request.POST)
        if form.is_valid():
            # Get form data before saving (since we're not storing personal data)
            attendant_name = form.cleaned_data["attendant_name"]
            attendant_email = form.cleaned_data["attendant_email"]
            attendant_phone = form.cleaned_data.get("attendant_phone_number", "")

            assignment = form.save()

            # Send user confirmation email (using form data, not stored data)
            send_mail(
                subject=_("Registration Confirmation - %(collection)s")
                % {"collection": assignment.period_collection.collection.name},
                message=(
                    _(
                        "Dear %(name)s,\n\n"
                        "Your registration is confirmed.\n\n"
                        "Collection: %(collection)s\n"
                        "Period: %(period)s\n\n"
                        "Deletion link: %(link)s\n\n"
                        "Important: You will need to provide your email address to confirm deletion.\n\n"
                        "Best regards"
                    )
                    % {
                        "name": attendant_name,
                        "collection": assignment.period_collection.collection.name,
                        "period": assignment.period_collection.period.name,
                        "link": request.build_absolute_uri("/delete/" + str(assignment.deletion_token) + "/"),
                    }
                ),
                from_email=get_email_config("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                recipient_list=[attendant_email],
                fail_silently=True,
            )

            # Send maintainer notification with user email as reply-to (using form data, not stored data)
            # Only include maintainers with valid email addresses
            maintainers = CollectionMaintainer.objects.filter(
                collection=assignment.period_collection.collection,
                maintainer__user__email__isnull=False,
                maintainer__user__email__gt="",
            )
            if maintainers.exists():
                maintainer_emails: list[str] = [
                    m.maintainer.user.email
                    for m in maintainers
                    if m.maintainer.user.email and m.maintainer.user.email.strip()
                ]
                phone_info = f"\nPhone: {attendant_phone}" if attendant_phone else ""

                # Create email message with reply-to functionality
                email_message = EmailMessage(
                    subject=_("New Registration - %(collection)s")
                    % {"collection": assignment.period_collection.collection.name},
                    body=(
                        _(
                            "New participant registered:\n\n"
                            "Name: %(name)s\n"
                            "Email: %(email)s%(phone)s\n"
                            "Collection: %(collection)s\n"
                            "Period: %(period)s\n\n"
                            "Registration Date: %(date)s\n"
                            "Deletion Token: %(token)s\n\n"
                            "Note: Personal data is not stored in the system for privacy. "
                            "This email is sent directly from the user's email address."
                        )
                        % {
                            "name": attendant_name,
                            "email": attendant_email,
                            "phone": phone_info,
                            "collection": assignment.period_collection.collection.name,
                            "period": assignment.period_collection.period.name,
                            "date": assignment.period_collection.period.name,
                            "token": assignment.deletion_token,
                        }
                    ),
                    from_email=get_email_config("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                    to=maintainer_emails,
                    reply_to=[attendant_email],
                )
                # Only send if we have valid email addresses
                if maintainer_emails:
                    email_message.send(fail_silently=True)

            messages.success(
                request,
                _("Registration successful! Check your email for confirmation."),
            )
            return redirect("registration")
    else:
        form = PeriodAssignmentForm()

    return render(request, "adoration/registration.html", {"form": form})


def get_collection_periods(request: HttpRequest, collection_id: int) -> JsonResponse:
    """AJAX endpoint to get periods for a specific collection.

    Args:
        request: HTTP request object
        collection_id: ID of the collection to get periods for

    Returns:
        JsonResponse: JSON containing periods data or error message

    Raises:
        DoesNotExist: When collection is not found or not available in current language
    """
    # Get current language
    current_language = translation.get_language() or "en"

    try:
        collection = Collection.objects.get(id=collection_id, enabled=True)
        # Check if collection is available in current language
        if not collection.is_available_in_language(current_language):
            raise Collection.DoesNotExist
    except Collection.DoesNotExist:
        return JsonResponse({"error": str(_("Collection not found"))}, status=404)

    try:
        period_collections = PeriodCollection.objects.filter(collection=collection).select_related("period")

        periods_data: list[dict[str, Any]] = []
        for pc in period_collections:
            # Get current assignment count
            current_count: int = PeriodAssignment.objects.filter(period_collection=pc).count()

            periods_data.append(
                {
                    "id": pc.pk,
                    "name": pc.period.name,
                    "description": pc.period.description,
                    "current_count": current_count,
                }
            )

        return JsonResponse({"periods": periods_data})

    except Exception:
        return JsonResponse({"error": str(_("Failed to load periods"))}, status=500)


def get_collection_maintainers(request: HttpRequest, collection_id: int) -> JsonResponse:
    """AJAX endpoint to get maintainer information for a specific collection.

    Args:
        request: HTTP request object
        collection_id: ID of the collection to get maintainers for

    Returns:
        JsonResponse: JSON containing maintainer data or error message

    Raises:
        DoesNotExist: When collection is not found or not available in current language
    """
    # Get current language
    current_language = translation.get_language() or "en"

    try:
        collection = Collection.objects.get(id=collection_id, enabled=True)
        # Check if collection is available in current language
        if not collection.is_available_in_language(current_language):
            raise Collection.DoesNotExist
    except Collection.DoesNotExist:
        return JsonResponse({"error": str(_("Collection not found"))}, status=404)

    try:
        # Get maintainers with valid email addresses
        maintainers = CollectionMaintainer.objects.filter(
            collection=collection,
            maintainer__user__email__isnull=False,
            maintainer__user__email__gt="",
        ).select_related("maintainer__user")

        maintainers_data: list[dict[str, Any]] = []
        for maintainer in maintainers:
            user = maintainer.maintainer.user
            maintainer_info = {
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "country": maintainer.maintainer.country,
            }
            # Only include phone number if it exists and is not empty
            if maintainer.maintainer.phone_number:
                maintainer_info["phone"] = maintainer.maintainer.phone_number

            maintainers_data.append(maintainer_info)

        return JsonResponse({"collection_name": collection.name, "maintainers": maintainers_data})

    except Exception:
        return JsonResponse({"error": str(_("Failed to load maintainer information"))}, status=500)


def delete_assignment(request: HttpRequest, token: str) -> HttpResponse:
    """Handle deletion of period assignment using deletion token and email verification.

    Args:
        request: HTTP request object
        token: Unique deletion token for the assignment

    Returns:
        HttpResponse: Confirmation page or redirect after deletion
    """
    assignment = get_object_or_404(PeriodAssignment, deletion_token=token)

    if request.method == "POST":
        form = DeletionConfirmForm(assignment, request.POST)
        if form.is_valid():
            # Get user email for notifications before deleting
            user_email = form.cleaned_data["email"]

            # Send maintainer notification about deletion
            # Only include maintainers with valid email addresses
            maintainers = CollectionMaintainer.objects.filter(
                collection=assignment.period_collection.collection,
                maintainer__user__email__isnull=False,
                maintainer__user__email__gt="",
            )
            if maintainers.exists():
                maintainer_emails: list[str] = [
                    m.maintainer.user.email
                    for m in maintainers
                    if m.maintainer.user.email and m.maintainer.user.email.strip()
                ]

                # Create email message for deletion notification
                email_message = EmailMessage(
                    subject=_("Registration Cancelled - %(collection)s")
                    % {"collection": assignment.period_collection.collection.name},
                    body=(
                        _(
                            "A participant has cancelled their registration:\n\n"
                            "Email: %(email)s\n"
                            "Collection: %(collection)s\n"
                            "Period: %(period)s\n\n"
                            "The participant voluntarily cancelled their registration using the deletion link."
                        )
                        % {
                            "email": user_email,
                            "collection": assignment.period_collection.collection.name,
                            "period": assignment.period_collection.period.name,
                        }
                    ),
                    from_email=get_email_config("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                    to=maintainer_emails,
                    reply_to=[user_email],
                )
                # Only send if we have valid email addresses
                if maintainer_emails:
                    email_message.send(fail_silently=True)

            assignment.delete()
            messages.success(request, _("Registration cancelled successfully."))
            return redirect("registration")
    else:
        form = DeletionConfirmForm(assignment)

    return render(
        request,
        "adoration/delete_confirm.html",
        {"assignment": assignment, "form": form},
    )


def get_email_config(config_name: str, default_value: str | None = None) -> str | None:
    """Get email configuration value from Config model.

    Args:
        config_name: Name of the configuration setting
        default_value: Default value if config not found

    Returns:
        Configuration value or default value if not found
    """
    try:
        config = Config.objects.get(name=config_name)
        value: str = config.value
        return value
    except Config.DoesNotExist:
        return default_value
