"""
Views for the maintainer panel.

This module contains views that allow maintainers to manage collections,
periods, and period assignments through a dedicated admin interface.
"""

from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import CollectionForm
from .models import (
    Collection,
    CollectionMaintainer,
    Maintainer,
    Period,
    PeriodAssignment,
    PeriodCollection,
)


class MaintainerRequiredMixin:
    """Mixin to ensure user is a maintainer."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Check if user is a maintainer before allowing access."""
        if not request.user.is_authenticated:
            return redirect("login")

        try:
            request.user.maintainer
        except Maintainer.DoesNotExist:
            raise PermissionDenied("You must be a maintainer to access this page.")

        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class MaintainerDashboardView(MaintainerRequiredMixin, ListView):
    """Main dashboard view for maintainers."""

    template_name = "adoration/maintainer/dashboard.html"
    context_object_name = "collections"

    def get_queryset(self):
        """Get collections managed by the current maintainer."""
        maintainer = self.request.user.maintainer
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related(
            "periods", "collectionmaintainer_set__maintainer__user"
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        maintainer = self.request.user.maintainer

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
class CollectionListView(MaintainerRequiredMixin, ListView):
    """List view for collections managed by maintainer."""

    model = Collection
    template_name = "adoration/maintainer/collection_list.html"
    context_object_name = "collections"
    paginate_by = 20

    def get_queryset(self):
        """Get collections managed by the current maintainer."""
        maintainer = self.request.user.maintainer
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related("periods")


@method_decorator(login_required, name="dispatch")
class CollectionCreateView(MaintainerRequiredMixin, CreateView):
    """Create view for collections."""

    model = Collection
    form_class = CollectionForm
    template_name = "adoration/maintainer/collection_form.html"
    success_url = reverse_lazy("maintainer:collection_list")

    def form_valid(self, form):
        """Save collection and automatically assign current user as maintainer."""
        response = super().form_valid(form)

        # Automatically assign the current user as a maintainer
        maintainer = self.request.user.maintainer
        CollectionMaintainer.objects.create(collection=self.object, maintainer=maintainer)

        messages.success(
            self.request,
            _("Collection '{}' created successfully. You are now a maintainer of this collection.").format(
                self.object.name
            ),
        )
        return response


@method_decorator(login_required, name="dispatch")
class CollectionUpdateView(MaintainerRequiredMixin, UpdateView):
    """Update view for collections."""

    model = Collection
    form_class = CollectionForm
    template_name = "adoration/maintainer/collection_form.html"
    context_object_name = "collection"
    success_url = reverse_lazy("maintainer:collection_list")

    def get_queryset(self):
        """Only allow editing collections managed by current maintainer."""
        maintainer = self.request.user.maintainer
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer)

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("Collection '{}' updated successfully.").format(self.object.name),
        )
        return response


@method_decorator(login_required, name="dispatch")
class CollectionDetailView(MaintainerRequiredMixin, DetailView):
    """Detail view for collections."""

    model = Collection
    template_name = "adoration/maintainer/collection_detail.html"
    context_object_name = "collection"

    def get_queryset(self):
        """Only show collections managed by current maintainer."""
        maintainer = self.request.user.maintainer
        return Collection.objects.filter(collectionmaintainer__maintainer=maintainer).prefetch_related(
            "periods",
            "collectionmaintainer_set__maintainer__user",
            "periodcollection_set__periodassignment_set",
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        collection = self.object

        # Get periods assigned to this collection
        period_collections = (
            PeriodCollection.objects.filter(collection=collection)
            .select_related("period")
            .prefetch_related("periodassignment_set")
        )

        # Get unassigned periods
        assigned_period_ids = collection.periods.values_list("id", flat=True)
        unassigned_periods = Period.objects.exclude(id__in=assigned_period_ids)

        context.update(
            {
                "period_collections": period_collections,
                "unassigned_periods": unassigned_periods,
                "total_assignments": sum(pc.periodassignment_set.count() for pc in period_collections),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class PeriodListView(MaintainerRequiredMixin, ListView):
    """List view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_list.html"
    context_object_name = "periods"
    paginate_by = 20


@method_decorator(login_required, name="dispatch")
class PeriodCreateView(MaintainerRequiredMixin, CreateView):
    """Create view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_form.html"
    fields = ["name", "description"]
    success_url = reverse_lazy("maintainer:period_list")

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("Period '{}' created successfully.").format(self.object.name),
        )
        return response


@method_decorator(login_required, name="dispatch")
class PeriodUpdateView(MaintainerRequiredMixin, UpdateView):
    """Update view for periods."""

    model = Period
    template_name = "adoration/maintainer/period_form.html"
    fields = ["name", "description"]
    success_url = reverse_lazy("maintainer:period_list")

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            _("Period '{}' updated successfully.").format(self.object.name),
        )
        return response


@login_required
@permission_required("adoration.add_periodcollection", raise_exception=True)
def assign_period_to_collection(request: HttpRequest) -> JsonResponse:
    """AJAX view to assign a period to a collection."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer = request.user.maintainer
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

        # Create period-collection relationship
        period_collection, created = PeriodCollection.objects.get_or_create(collection=collection, period=period)

        if created:
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
    """AJAX view to remove a period from a collection."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"})

    try:
        maintainer = request.user.maintainer
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
@permission_required("adoration.add_maintainer", raise_exception=True)
def promote_user_to_maintainer(request: HttpRequest) -> JsonResponse:
    """AJAX view to promote a user to maintainer."""
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
            maintainer = Maintainer.objects.create(user=user, country=country, phone_number=phone_number)

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
class AssignmentListView(MaintainerRequiredMixin, ListView):
    """List view for period assignments managed by maintainer."""

    model = PeriodAssignment
    template_name = "adoration/maintainer/assignment_list.html"
    context_object_name = "assignments"
    paginate_by = 50

    def get_queryset(self):
        """Get assignments for collections managed by current maintainer."""
        maintainer = self.request.user.maintainer
        return (
            PeriodAssignment.objects.filter(period_collection__collection__collectionmaintainer__maintainer=maintainer)
            .select_related("period_collection__collection", "period_collection__period")
            .order_by("-id")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add filter context."""
        context = super().get_context_data(**kwargs)
        maintainer = self.request.user.maintainer

        # Get collections for filtering
        collections = Collection.objects.filter(collectionmaintainer__maintainer=maintainer)

        context.update(
            {
                "collections": collections,
                "selected_collection": self.request.GET.get("collection"),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class UserPromotionView(MaintainerRequiredMixin, ListView):
    """View for promoting users to maintainers."""

    model = User
    template_name = "adoration/maintainer/user_promotion.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        """Get users who are not maintainers yet."""
        return User.objects.filter(maintainer__isnull=True, email__isnull=False).exclude(email="").order_by("username")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add search context."""
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
