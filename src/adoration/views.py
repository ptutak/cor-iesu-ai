from typing import Any

from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

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
                subject=f"Registration Confirmation - {assignment.period_collection.collection.name}",
                message=(
                    f"Dear {attendant_name},\n\n"
                    f"Your registration is confirmed.\n\n"
                    f"Collection: {assignment.period_collection.collection.name}\n"
                    f"Period: {assignment.period_collection.period.name}\n\n"
                    f"Deletion link: "
                    f"{request.build_absolute_uri('/delete/' + str(assignment.deletion_token) + '/')}\n\n"
                    f"Important: You will need to provide your email address to confirm deletion.\n\n"
                    f"Best regards"
                ),
                from_email=get_email_config("DEFAULT_FROM_EMAIL", "noreply@example.com") or "noreply@example.com",
                recipient_list=[attendant_email],
                fail_silently=True,
            )

            # Send maintainer notification with user email as reply-to (using form data, not stored data)
            maintainers = CollectionMaintainer.objects.filter(collection=assignment.period_collection.collection)
            if maintainers.exists():
                maintainer_emails: list[str] = [m.maintainer.user.email for m in maintainers]
                phone_info = f"\nPhone: {attendant_phone}" if attendant_phone else ""

                # Try to use user email as sender, fallback to system email
                from_email = attendant_email

                # Create email message with reply-to functionality
                email_message = EmailMessage(
                    subject=f"New Registration - {assignment.period_collection.collection.name}",
                    body=(
                        f"New participant registered:\n\n"
                        f"Name: {attendant_name}\n"
                        f"Email: {attendant_email}{phone_info}\n"
                        f"Collection: {assignment.period_collection.collection.name}\n"
                        f"Period: {assignment.period_collection.period.name}\n\n"
                        f"Registration Date: {assignment.period_collection.period.name}\n"
                        f"Deletion Token: {assignment.deletion_token}\n\n"
                        f"Note: Personal data is not stored in the system for privacy. "
                        f"This email is sent directly from the user's email address."
                    ),
                    from_email=from_email,
                    to=maintainer_emails,
                    reply_to=[attendant_email] if from_email != attendant_email else None,
                )
                email_message.send(fail_silently=True)

            messages.success(request, "Registration successful! Check your email for confirmation.")
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
    """
    try:
        collection = get_object_or_404(Collection, id=collection_id, enabled=True)
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
        return JsonResponse({"error": "Failed to load periods"}, status=500)


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
            maintainers = CollectionMaintainer.objects.filter(collection=assignment.period_collection.collection)
            if maintainers.exists():
                maintainer_emails: list[str] = [m.maintainer.user.email for m in maintainers]

                # Create email message for deletion notification
                email_message = EmailMessage(
                    subject=f"Registration Cancelled - {assignment.period_collection.collection.name}",
                    body=(
                        f"A participant has cancelled their registration:\n\n"
                        f"Email: {user_email}\n"
                        f"Collection: {assignment.period_collection.collection.name}\n"
                        f"Period: {assignment.period_collection.period.name}\n\n"
                        f"The participant voluntarily cancelled their registration using the deletion link."
                    ),
                    from_email=user_email,
                    to=maintainer_emails,
                    reply_to=[user_email],
                )
                email_message.send(fail_silently=True)

            assignment.delete()
            messages.success(request, "Registration cancelled successfully.")
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
