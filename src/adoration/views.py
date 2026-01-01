from typing import Optional

from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PeriodAssignmentForm
from .models import (
    Collection,
    CollectionMaintainer,
    Config,
    PeriodAssignment,
    PeriodCollection,
)


def registration_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PeriodAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save()

            # Send user confirmation email
            send_mail(
                subject=f"Registration Confirmation - {assignment.period_collection.collection.name}",
                message=f"Dear {assignment.attendant_name},\n\nYour registration is confirmed.\n\nCollection: {assignment.period_collection.collection.name}\nPeriod: {assignment.period_collection.period.name}\n\nDeletion link: {request.build_absolute_uri('/delete/' + assignment.deletion_token + '/')}\n\nBest regards",
                from_email=get_email_config("DEFAULT_FROM_EMAIL", "noreply@example.com"),
                recipient_list=[assignment.attendant_email],
                fail_silently=True,
            )

            # Send maintainer notification
            maintainers = CollectionMaintainer.objects.filter(collection=assignment.period_collection.collection)
            if maintainers.exists():
                maintainer_emails = [m.maintainer.user.email for m in maintainers]
                send_mail(
                    subject=f"New Registration - {assignment.period_collection.collection.name}",
                    message=f"New participant registered:\n\nName: {assignment.attendant_name}\nEmail: {assignment.attendant_email}\nCollection: {assignment.period_collection.collection.name}\nPeriod: {assignment.period_collection.period.name}",
                    from_email=get_email_config("DEFAULT_FROM_EMAIL", "noreply@example.com"),
                    recipient_list=maintainer_emails,
                    fail_silently=True,
                )

            messages.success(request, "Registration successful! Check your email for confirmation.")
            return redirect("registration")
    else:
        form = PeriodAssignmentForm()

    return render(request, "adoration/registration.html", {"form": form})


def get_collection_periods(request: HttpRequest, collection_id: int) -> JsonResponse:
    """AJAX endpoint to get periods for a specific collection"""
    try:
        collection = get_object_or_404(Collection, id=collection_id, enabled=True)
        period_collections = PeriodCollection.objects.filter(collection=collection).select_related("period")

        periods_data = []
        for pc in period_collections:
            # Get current assignment count
            current_count = PeriodAssignment.objects.filter(period_collection=pc).count()

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
    assignment = get_object_or_404(PeriodAssignment, deletion_token=token)

    if request.method == "POST":
        assignment.delete()
        messages.success(request, "Registration cancelled successfully.")
        return redirect("registration")

    return render(request, "adoration/delete_confirm.html", {"assignment": assignment})


def get_email_config(config_name: str, default_value: str | None = None) -> str | None:
    try:
        config = Config.objects.get(name=config_name)
        return config.value
    except Config.DoesNotExist:
        return default_value
