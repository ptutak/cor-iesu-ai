"""
Views for the maintainer panel.

This module contains views that allow maintainers to manage collections,
periods, and period assignments through a dedicated admin interface.
"""

from typing import TYPE_CHECKING, Any, cast

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import CollectionForm
from .models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    MaintainerPeriod,
    Period,
    PeriodAssignment,
    PeriodCollection,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    class UserWithMaintainer(AbstractUser):
        """Type hint for User with maintainer relationship."""

        maintainer: Maintainer


class MaintainerRequiredMixin:
    """Mixin to ensure user is a maintainer.

    This mixin checks that the current user is authenticated and has a
    maintainer profile before allowing access to the view.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Check if user is a maintainer before allowing access.

        Args:
            request: HTTP request object
            args: Additional positional arguments
            kwargs: Additional keyword arguments

        Returns:
            HTTP response

        Raises:
            PermissionDenied: If user is not a maintainer
        """
        if not request.user.is_authenticated:
            return redirect("login")

        try:
            getattr(request.user, "maintainer")
        except Maintainer.DoesNotExist:
            raise PermissionDenied("You must be a maintainer to access this page.")

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc,no-any-return]


@method_decorator(login_required, name="dispatch")
class MaintainerDashboardView(MaintainerRequiredMixin, ListView[Collection]):
    """Main dashboard view for maintainers."""

    template_name = "adoration/maintainer/dashboard.html"
    context_object_name = "collections"

    def get_queryset(self) -> Any:
        """Get collections managed by the current maintainer.

        Returns:
            QuerySet of collections managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related(
            "periods", "collectionmaintainer_set__maintainer__user"
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with dashboard statistics
        """
        context = super().get_context_data(**kwargs)
        maintainer: Maintainer = getattr(self.request.user, "maintainer")

        context.update(
            {
                "total_collections": self.get_queryset().count(),
                "total_periods": Period.objects.count(),
                "total_assignments": PeriodAssignment.objects.filter(
                    period_collection__collection__in=self.get_queryset()
                ).count(),
                "maintainer": maintainer,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class CollectionListView(MaintainerRequiredMixin, ListView[Collection]):
    """List view for collections managed by maintainer."""

    model = Collection
    template_name = "adoration/maintainer/collection_list.html"
    context_object_name = "collections"

    def get_queryset(self) -> models.QuerySet[Collection]:
        """Get collections managed by the current maintainer.

        Returns:
            QuerySet of Collection objects managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related("periods")


@method_decorator(login_required, name="dispatch")
class CollectionCreateView(MaintainerRequiredMixin, CreateView[Collection, Any]):
    """Create view for collections."""

    model = Collection
    form_class = CollectionForm
    template_name = "adoration/maintainer/collection_form.html"
    success_url = reverse_lazy("maintainer:collection_list")

    def form_valid(self, form: CollectionForm) -> HttpResponse:
        """Save collection and automatically assign current user as maintainer.

        Args:
            form: The valid form instance

        Returns:
            HTTP response redirecting to collection list
        """
        response = super().form_valid(form)

        # Automatically assign the current user as a maintainer
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        CollectionMaintainer.objects.create(collection=self.object, maintainer=maintainer)

        messages.success(
            self.request,
            _("Collection '{}' created successfully. You are now a maintainer of this collection.").format(
                cast(Collection, self.object).name
            ),
        )
        return response


@method_decorator(login_required, name="dispatch")
class CollectionUpdateView(MaintainerRequiredMixin, UpdateView[Collection, Any]):
    """Update view for collections."""

    model = Collection
    form_class = CollectionForm
    template_name = "adoration/maintainer/collection_form.html"
    context_object_name = "collection"
    success_url = reverse_lazy("maintainer:collection_list")

    def get_queryset(self) -> models.QuerySet[Collection]:
        """Only allow editing collections managed by current maintainer.

        Returns:
            QuerySet of Collection objects managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer)

    def form_valid(self, form: CollectionForm) -> HttpResponse:
        """Handle successful form submission.

        Args:
            form: The valid form instance

        Returns:
            HTTP response redirecting to collection list
        """
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("Collection '{}' updated successfully.").format(self.object.name),
        )
        return response


@method_decorator(login_required, name="dispatch")
class CollectionDetailView(MaintainerRequiredMixin, DetailView[Collection]):
    """Detail view for collections."""

    model = Collection
    template_name = "adoration/maintainer/collection_detail.html"
    context_object_name = "collection"

    def get_queryset(self) -> models.QuerySet[Collection]:
        """Only show collections managed by current maintainer.

        Returns:
            QuerySet of Collection objects managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related(
            "periods",
            "collectionmaintainer_set__maintainer__user",
            "periodcollection_set__periodassignment_set",
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with period collections and assignments data
        """
        context = super().get_context_data(**kwargs)
        collection = self.object
        maintainer: Maintainer = getattr(self.request.user, "maintainer")

        # Get periods assigned to this collection AND to the current maintainer
        period_collections = (
            PeriodCollection.objects.filter(collection=collection, period__maintainerperiod__maintainer=maintainer)
            .select_related("period")
            .prefetch_related("periodassignment_set")
        )

        # Get maintainer's periods that are not assigned to this collection
        maintainer_period_ids = MaintainerPeriod.objects.filter(maintainer=maintainer).values_list(
            "period_id", flat=True
        )

        assigned_period_ids = collection.periods.filter(id__in=maintainer_period_ids).values_list("id", flat=True)

        unassigned_periods = Period.objects.filter(id__in=maintainer_period_ids).exclude(id__in=assigned_period_ids)

        context.update(
            {
                "period_collections": period_collections,
                "unassigned_periods": unassigned_periods,
                "total_assignments": sum(
                    pc.periodassignment_set.count() for pc in period_collections  # type: ignore[attr-defined]
                ),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class CollectionDeleteView(MaintainerRequiredMixin, DeleteView[Collection, Any]):
    """Delete view for collections."""

    model = Collection
    template_name = "adoration/maintainer/collection_confirm_delete.html"
    success_url = reverse_lazy("maintainer:collection_list")
    context_object_name = "collection"

    def get_queryset(self) -> QuerySet[Collection]:
        """Get collections that the current maintainer can delete.

        Returns:
            QuerySet of Collection objects managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related(
            "periods", "collectionmaintainer_set__maintainer__user"
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with collection usage statistics
        """
        context = super().get_context_data(**kwargs)
        collection = self.get_object()

        # Get usage statistics
        period_collections = PeriodCollection.objects.filter(collection=collection)
        total_assignments = sum(
            PeriodAssignment.objects.filter(period_collection=pc).count() for pc in period_collections
        )

        context.update(
            {
                "total_periods": period_collections.count(),
                "total_assignments": total_assignments,
                "period_collections": period_collections.select_related("period"),
                "maintainers": CollectionMaintainer.objects.filter(collection=collection).select_related(
                    "maintainer__user"
                ),
            }
        )
        return context

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle DELETE request.

        Args:
            request: HTTP request object
            args: Additional positional arguments
            kwargs: Additional keyword arguments

        Returns:
            HTTP response redirecting to collection list
        """
        collection = self.get_object()
        messages.success(
            request,
            _("Collection '{}' deleted successfully.").format(collection.name),
        )
        return super().delete(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class PeriodListView(MaintainerRequiredMixin, ListView[Period]):
    """List view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_list.html"
    context_object_name = "periods"
    paginate_by = 20

    def get_queryset(self) -> Any:
        """Get queryset with annotations for collections and assignments count.

        Only shows periods assigned to the current maintainer.

        Returns:
            QuerySet of Period objects with collection_count and assignment_count annotations
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")

        return (
            Period.objects.filter(maintainerperiod__maintainer=maintainer)
            .annotate(
                collection_count=Count("periodcollection", distinct=True),
                assignment_count=Count("periodcollection__periodassignment", distinct=True),
            )
            .order_by("name")
        )


@method_decorator(login_required, name="dispatch")
class PeriodCreateView(MaintainerRequiredMixin, CreateView[Period, Any]):
    """Create view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_form.html"
    fields = ["name", "description"]
    success_url = reverse_lazy("maintainer:period_list")

    def form_valid(self, form: Any) -> HttpResponse:
        """Handle successful form submission and assign period to current maintainer.

        Args:
            form: The valid form instance

        Returns:
            HTTP response redirecting to period list
        """
        response = super().form_valid(form)

        # Automatically assign the created period to the current maintainer
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        MaintainerPeriod.objects.get_or_create(maintainer=maintainer, period=cast(Period, self.object))

        messages.success(
            self.request,
            _("Period '{}' created and assigned to you successfully.").format(cast(Period, self.object).name),
        )
        return response


@method_decorator(login_required, name="dispatch")
class PeriodUpdateView(MaintainerRequiredMixin, UpdateView[Period, Any]):
    """Update view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_form.html"
    fields = ["name", "description"]
    success_url = reverse_lazy("maintainer:period_list")

    def form_valid(self, form: Any) -> HttpResponse:
        """Handle successful form submission.

        Args:
            form: The valid form instance

        Returns:
            HTTP response redirecting to period list
        """
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("Period '{}' updated successfully.").format(self.object.name),
        )
        return response


@method_decorator(login_required, name="dispatch")
class PeriodDeleteView(MaintainerRequiredMixin, DeleteView[Period, Any]):
    """Remove period from maintainer's management instead of deleting the period."""

    model = Period
    template_name = "adoration/maintainer/period_confirm_delete.html"
    success_url = reverse_lazy("maintainer:period_list")
    context_object_name = "period"

    def get_queryset(self) -> Any:
        """Only show periods assigned to the current maintainer.

        Returns:
            QuerySet of Period objects managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return Period.objects.filter(maintainerperiod__maintainer=maintainer)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with period usage statistics for this maintainer
        """
        context = super().get_context_data(**kwargs)
        period = self.get_object()
        maintainer: Maintainer = getattr(self.request.user, "maintainer")

        # Get usage statistics for this maintainer's collections only
        period_collections = PeriodCollection.objects.filter(
            period=period, collection__collectionmaintainer__maintainer=maintainer
        )
        total_assignments = sum(
            PeriodAssignment.objects.filter(period_collection=pc).count() for pc in period_collections
        )

        context.update(
            {
                "total_collections": period_collections.count(),
                "total_assignments": total_assignments,
                "period_collections": period_collections.select_related("collection"),
                "is_maintainer_removal": True,  # Flag to indicate this is not a full deletion
            }
        )
        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle POST request for period removal.

        Args:
            request: HTTP request object
            args: Additional positional arguments
            kwargs: Additional keyword arguments

        Returns:
            HTTP response for period removal
        """
        return self.delete(request, *args, **kwargs)

    def form_valid(self, form: Any) -> HttpResponse:
        """Override form_valid to prevent default deletion.

        Args:
            form: The form instance (unused in this override)

        Returns:
            HTTP response from delete method
        """
        return self.delete(self.request)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle DELETE request by removing maintainer-period relationship.

        Args:
            request: HTTP request object
            args: Additional positional arguments
            kwargs: Additional keyword arguments

        Returns:
            HTTP response redirecting to period list
        """
        period = self.get_object()
        maintainer: Maintainer = getattr(request.user, "maintainer")

        # Check if there are any assignments in maintainer's collections
        period_collections = PeriodCollection.objects.filter(
            period=period, collection__collectionmaintainer__maintainer=maintainer
        )
        total_assignments = sum(
            PeriodAssignment.objects.filter(period_collection=pc).count() for pc in period_collections
        )

        if total_assignments > 0:
            messages.error(
                request,
                _("Cannot remove period '{}' - it has {} active assignments in your collections.").format(
                    period.name, total_assignments
                ),
            )
            return redirect(self.success_url)

        # Remove maintainer-period relationship and period-collection relationships
        try:
            maintainer_period = MaintainerPeriod.objects.get(maintainer=maintainer, period=period)
            maintainer_period.delete()

            # Also remove from any collections managed by this maintainer
            period_collections.delete()

            messages.success(
                request,
                _("Period '{}' removed from your management successfully.").format(period.name),
            )
        except MaintainerPeriod.DoesNotExist:
            messages.error(
                request,
                _("Period '{}' is not assigned to you.").format(period.name),
            )

        return redirect(self.success_url)


@login_required
@permission_required("adoration.add_periodcollection", raise_exception=True)
def assign_period_to_collection(request: HttpRequest) -> JsonResponse:
    """AJAX view to assign a period to a collection.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")
    except Maintainer.DoesNotExist:
        return JsonResponse({"success": False, "error": "User is not a maintainer"})

    collection_id = request.POST.get("collection_id")
    period_id = request.POST.get("period_id")
    period_name = request.POST.get("period_name")

    if not collection_id:
        return JsonResponse({"success": False, "error": "Missing collection ID"})

    if not period_id and not period_name:
        return JsonResponse({"success": False, "error": "Missing period ID or name"})

    try:
        # Verify maintainer has access to this collection
        collection = Collection.objects.get(id=collection_id, collectionmaintainer__maintainer=maintainer)

        # Get or create the period
        if period_id:
            try:
                period = Period.objects.get(id=period_id)
            except Period.DoesNotExist:
                return JsonResponse({"success": False, "error": "Period not found"})
        else:
            # Create new period if it doesn't exist
            period, created = Period.objects.get_or_create(name=period_name, defaults={"description": ""})

        # Ensure maintainer has access to this period
        maintainer_period, mp_created = MaintainerPeriod.objects.get_or_create(maintainer=maintainer, period=period)

        # Create period-collection relationship
        period_collection, pc_created = PeriodCollection.objects.get_or_create(collection=collection, period=period)

        if pc_created:
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Period '{}' assigned to collection '{}'.").format(period.name, collection.name),
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Period is already assigned to this collection."),
                }
            )

    except Collection.DoesNotExist:
        return JsonResponse({"success": False, "error": "Collection not found or access denied"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@permission_required("adoration.delete_periodcollection", raise_exception=True)
def remove_period_from_collection(request: HttpRequest) -> JsonResponse:
    """AJAX view to remove a period from a collection.

    This removes the period-collection relationship but never deletes the actual period.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")
    except Maintainer.DoesNotExist:
        return JsonResponse({"success": False, "error": "User is not a maintainer"})

    collection_id = request.POST.get("collection_id")
    period_id = request.POST.get("period_id")

    if not collection_id or not period_id:
        return JsonResponse({"success": False, "error": "Missing collection or period ID"})

    try:
        # Verify maintainer has access to this collection
        collection = Collection.objects.get(id=collection_id, collectionmaintainer__maintainer=maintainer)
        period = get_object_or_404(Period, id=period_id)

        # Verify maintainer has access to this period
        if not MaintainerPeriod.objects.filter(maintainer=maintainer, period=period).exists():
            return JsonResponse({"success": False, "error": "Access denied to this period"})

        # Remove period-collection relationship
        period_collection = PeriodCollection.objects.get(collection=collection, period=period)

        # Check if there are any assignments
        assignment_count = PeriodAssignment.objects.filter(period_collection=period_collection).count()

        if assignment_count > 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Cannot remove period '{}' - it has {} active assignments.").format(
                        period.name, assignment_count
                    ),
                }
            )

        # Only remove the period-collection relationship, never the period itself
        period_collection.delete()

        return JsonResponse(
            {
                "success": True,
                "message": _("Period '{}' removed from collection '{}'.").format(period.name, collection.name),
            }
        )

    except Collection.DoesNotExist:
        return JsonResponse({"success": False, "error": "Collection not found or access denied"})
    except PeriodCollection.DoesNotExist:
        return JsonResponse({"success": False, "error": "Period is not assigned to this collection"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def assign_period_to_maintainer(request: HttpRequest) -> JsonResponse:
    """AJAX view to assign a period to the current maintainer.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")
    except Maintainer.DoesNotExist:
        return JsonResponse({"success": False, "error": "User is not a maintainer"})

    period_id = request.POST.get("period_id")
    period_name = request.POST.get("period_name")

    if not period_id and not period_name:
        return JsonResponse({"success": False, "error": "Missing period ID or name"})

    try:
        if period_id:
            period = get_object_or_404(Period, id=period_id)
        else:
            # Create new period if it doesn't exist
            period, created = Period.objects.get_or_create(name=period_name, defaults={"description": ""})

        # Create maintainer-period relationship
        maintainer_period, created = MaintainerPeriod.objects.get_or_create(maintainer=maintainer, period=period)

        if created:
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Period '{}' assigned to you successfully.").format(period.name),
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Period '{}' is already assigned to you.").format(period.name),
                }
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def remove_period_from_maintainer(request: HttpRequest) -> JsonResponse:
    """AJAX view to remove a period from the current maintainer.

    This removes the maintainer-period relationship but never deletes the actual period.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")
    except Maintainer.DoesNotExist:
        return JsonResponse({"success": False, "error": "User is not a maintainer"})

    period_id = request.POST.get("period_id")

    if not period_id:
        return JsonResponse({"success": False, "error": "Missing period ID"})

    try:
        period = get_object_or_404(Period, id=period_id)

        # Check if period is assigned to any collections managed by this maintainer
        period_collections = PeriodCollection.objects.filter(
            period=period, collection__collectionmaintainer__maintainer=maintainer
        )

        if period_collections.exists():
            # Check if there are any assignments
            total_assignments = sum(
                PeriodAssignment.objects.filter(period_collection=pc).count() for pc in period_collections
            )

            if total_assignments > 0:
                return JsonResponse(
                    {
                        "success": False,
                        "error": _(
                            "Cannot remove period '{}' - it has {} active assignments in your collections."
                        ).format(period.name, total_assignments),
                    }
                )

        # Remove maintainer-period relationship
        try:
            maintainer_period = MaintainerPeriod.objects.get(maintainer=maintainer, period=period)
            maintainer_period.delete()

            # Also remove from any collections managed by this maintainer
            period_collections.delete()

            return JsonResponse(
                {
                    "success": True,
                    "message": _("Period '{}' removed from your management.").format(period.name),
                }
            )

        except MaintainerPeriod.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": _("Period '{}' is not assigned to you.").format(period.name),
                }
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def assign_standard_periods_to_maintainer(request: HttpRequest) -> JsonResponse:
    """AJAX view to assign all 24 standard hour periods to the current maintainer.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")
    except Maintainer.DoesNotExist:
        return JsonResponse({"success": False, "error": "User is not a maintainer"})

    try:
        created_count = 0
        assigned_count = 0

        # Generate and assign 24 standard hour periods
        for hour in range(0, 24):
            period_name = f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00"

            # Create period if it doesn't exist
            period, period_created = Period.objects.get_or_create(
                name=period_name,
                defaults={"description": f"Adoration period from {hour:02d}:00 to {(hour + 1) % 24:02d}:00"},
            )

            if period_created:
                created_count += 1

            # Assign to maintainer if not already assigned
            maintainer_period, mp_created = MaintainerPeriod.objects.get_or_create(maintainer=maintainer, period=period)

            if mp_created:
                assigned_count += 1

        if created_count > 0 and assigned_count > 0:
            message = _("Created {} new periods and assigned {} periods to you successfully.").format(
                created_count, assigned_count
            )
        elif created_count > 0:
            message = _(
                "Created {} new periods successfully. All standard periods were already assigned to you."
            ).format(created_count)
        elif assigned_count > 0:
            message = _("Assigned {} standard periods to you successfully.").format(assigned_count)
        else:
            message = _("All 24 standard hour periods were already assigned to you.")

        return JsonResponse(
            {"success": True, "message": message, "created_count": created_count, "assigned_count": assigned_count}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@permission_required("adoration.add_maintainer", raise_exception=True)
def promote_user_to_maintainer(request: HttpRequest) -> JsonResponse:
    """AJAX view to promote a user to maintainer.

    Args:
        request: HTTP request object

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    user_id = request.POST.get("user_id")
    country = request.POST.get("country", "")
    phone_number = request.POST.get("phone_number", "")

    if not user_id:
        return JsonResponse({"success": False, "error": "Missing user ID"})

    try:
        user = get_object_or_404(User, id=user_id)

        # Check if user is already a maintainer
        if hasattr(user, "maintainer"):
            return JsonResponse(
                {
                    "success": False,
                    "error": _("User '{}' is already a maintainer.").format(user.username),
                }
            )

        # Check if user has an email
        if not user.email or not user.email.strip():
            return JsonResponse(
                {
                    "success": False,
                    "error": _("User must have an email address to become a maintainer."),
                }
            )

        # Create maintainer
        with transaction.atomic():
            Maintainer.objects.create(user=user, country=country, phone_number=phone_number)

            # Add user to maintainers group
            from django.contrib.auth.models import Group

            maintainer_group, created = Group.objects.get_or_create(name="Maintainers")
            user.groups.add(maintainer_group)

        return JsonResponse(
            {
                "success": True,
                "message": _("User '{}' promoted to maintainer successfully.").format(
                    user.get_full_name() or user.username
                ),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@method_decorator(login_required, name="dispatch")
class AssignmentListView(MaintainerRequiredMixin, ListView[PeriodAssignment]):
    """List view for period assignments managed by maintainer."""

    model = PeriodAssignment
    template_name = "adoration/maintainer/assignment_list.html"
    context_object_name = "assignments"
    paginate_by = 50

    def get_queryset(self) -> models.QuerySet[PeriodAssignment]:
        """Get assignments for collections managed by the current maintainer.

        Returns:
            QuerySet of PeriodAssignment objects for collections managed by the current maintainer
        """
        maintainer: Maintainer = getattr(self.request.user, "maintainer")
        return (
            PeriodAssignment.objects.filter(period_collection__collection__collectionmaintainer__maintainer=maintainer)
            .select_related("period_collection__collection", "period_collection__period")
            .order_by("-id")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add filter context.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with collections for filtering
        """
        context = super().get_context_data(**kwargs)
        maintainer: Maintainer = getattr(self.request.user, "maintainer")

        # Get collections for filtering
        collections = Collection.objects.filter(collectionmaintainer__maintainer=maintainer)

        context.update(
            {
                "collections": collections,
                "selected_collection": self.request.GET.get("collection"),
            }
        )
        return context


@login_required
@permission_required("adoration.delete_periodassignment", raise_exception=True)
def delete_assignment(request: HttpRequest, assignment_id: int) -> JsonResponse:
    """Delete a period assignment.

    Args:
        request: HTTP request object
        assignment_id: ID of the assignment to delete

    Returns:
        JSON response indicating success or failure
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer: Maintainer = getattr(request.user, "maintainer")

        # Get the assignment and verify maintainer has permission to delete it
        assignment = get_object_or_404(
            PeriodAssignment,
            id=assignment_id,
            period_collection__collection__collectionmaintainer__maintainer=maintainer,
        )

        collection_name = assignment.period_collection.collection.name
        period_name = assignment.period_collection.period.name

        assignment.delete()

        return JsonResponse(
            {
                "success": True,
                "message": _("Assignment deleted successfully from '{}' - '{}'.").format(collection_name, period_name),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@method_decorator(login_required, name="dispatch")
class UserPromotionView(MaintainerRequiredMixin, ListView[User]):
    """View for promoting users to maintainers."""

    model = User
    template_name = "adoration/maintainer/user_promotion.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self) -> models.QuerySet[User]:
        """Get users who are not maintainers yet.

        Returns:
            QuerySet of User objects who are not maintainers and have email addresses
        """
        return User.objects.filter(maintainer__isnull=True, email__isnull=False).exclude(email="").order_by("username")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add search context.

        Args:
            kwargs: Additional keyword arguments

        Returns:
            Context dictionary with search functionality
        """
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("search", "")

        if search_query:
            queryset = (
                self.get_queryset().filter(username__icontains=search_query)
                | self.get_queryset().filter(email__icontains=search_query)
                | self.get_queryset().filter(first_name__icontains=search_query)
                | self.get_queryset().filter(last_name__icontains=search_query)
            )
            context["users"] = queryset.distinct()

        context["search_query"] = search_query
        return context
