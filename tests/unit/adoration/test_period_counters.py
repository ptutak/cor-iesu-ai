"""
Tests for period counters (collections and assignments) in Maintainer Period List.

This module contains unit and integration tests to verify that the collection counter
and assignment counter show proper values in the Period list view.
"""

import pytest
from django.db.models import Count
from django.urls import reverse

from adoration.models import Collection, Period, PeriodAssignment, PeriodCollection


@pytest.mark.django_db
class TestPeriodCountersAnnotation:
    """Test the Period model annotations for collection_count and assignment_count."""

    def test_period_with_multiple_collections_and_assignments(self):
        """Test period with 2 collections and 3 assignments across them."""
        # Setup data
        period = Period.objects.create(name="Morning Prayer", description="6:00 AM - 7:00 AM")
        collection1 = Collection.objects.create(name="Collection 1", enabled=True)
        collection2 = Collection.objects.create(name="Collection 2", enabled=True)

        # Link period to collections
        pc1 = PeriodCollection.objects.create(period=period, collection=collection1)
        pc2 = PeriodCollection.objects.create(period=period, collection=collection2)

        # Create assignments: 2 in pc1, 1 in pc2
        pa1 = PeriodAssignment.create_with_email(email="test1@example.com", period_collection=pc1)
        pa1.save()
        pa2 = PeriodAssignment.create_with_email(email="test2@example.com", period_collection=pc1)
        pa2.save()
        pa3 = PeriodAssignment.create_with_email(email="test3@example.com", period_collection=pc2)
        pa3.save()

        # Query with annotations (same as in PeriodListView)
        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Assertions
        assert annotated_period.collection_count == 2
        assert annotated_period.assignment_count == 3

    def test_period_with_no_collections_and_no_assignments(self):
        """Test period with no collections and no assignments."""
        period = Period.objects.create(name="Evening Prayer", description="6:00 PM - 7:00 PM")

        # Query with annotations (same as in PeriodListView)
        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Assertions
        assert annotated_period.collection_count == 0
        assert annotated_period.assignment_count == 0

    def test_period_with_one_collection_no_assignments(self):
        """Test period with 1 collection but no assignments."""
        period = Period.objects.create(name="Afternoon Prayer", description="3:00 PM - 4:00 PM")
        collection = Collection.objects.create(name="Test Collection", enabled=True)
        PeriodCollection.objects.create(period=period, collection=collection)

        # Query with annotations
        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Assertions
        assert annotated_period.collection_count == 1
        assert annotated_period.assignment_count == 0

    def test_multiple_periods_with_different_counts(self):
        """Test multiple periods with different collection and assignment counts."""
        # Setup periods
        period1 = Period.objects.create(name="Morning", description="Morning period")
        period2 = Period.objects.create(name="Evening", description="Evening period")
        period3 = Period.objects.create(name="Night", description="Night period")

        # Setup collections
        collection1 = Collection.objects.create(name="Collection A", enabled=True)
        collection2 = Collection.objects.create(name="Collection B", enabled=True)

        # Period 1: 2 collections, 4 assignments
        pc1_1 = PeriodCollection.objects.create(period=period1, collection=collection1)
        pc1_2 = PeriodCollection.objects.create(period=period1, collection=collection2)
        pa1_1 = PeriodAssignment.create_with_email(email="p1_a1@example.com", period_collection=pc1_1)
        pa1_1.save()
        pa1_2 = PeriodAssignment.create_with_email(email="p1_a2@example.com", period_collection=pc1_1)
        pa1_2.save()
        pa1_3 = PeriodAssignment.create_with_email(email="p1_a3@example.com", period_collection=pc1_2)
        pa1_3.save()
        pa1_4 = PeriodAssignment.create_with_email(email="p1_a4@example.com", period_collection=pc1_2)
        pa1_4.save()

        # Period 2: 1 collection, 2 assignments
        pc2_1 = PeriodCollection.objects.create(period=period2, collection=collection1)
        pa2_1 = PeriodAssignment.create_with_email(email="p2_a1@example.com", period_collection=pc2_1)
        pa2_1.save()
        pa2_2 = PeriodAssignment.create_with_email(email="p2_a2@example.com", period_collection=pc2_1)
        pa2_2.save()

        # Period 3: 1 collection, 0 assignments
        PeriodCollection.objects.create(period=period3, collection=collection2)

        # Query with annotations
        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).order_by("name")

        periods = list(queryset)

        # Assertions (alphabetical order: Evening, Morning, Night)
        # Period 1 (Evening)
        assert periods[0].name == "Evening"
        assert periods[0].collection_count == 1
        assert periods[0].assignment_count == 2

        # Period 2 (Morning)
        assert periods[1].name == "Morning"
        assert periods[1].collection_count == 2
        assert periods[1].assignment_count == 4

        # Period 3 (Night)
        assert periods[2].name == "Night"
        assert periods[2].collection_count == 1
        assert periods[2].assignment_count == 0


@pytest.mark.django_db
class TestPeriodListViewCounters:
    """Test the PeriodListView integration with counter annotations."""

    @pytest.fixture
    def maintainer_with_permissions(self, maintainer_user):
        """Create a maintainer with necessary permissions."""
        from adoration.models import Maintainer

        maintainer = Maintainer.objects.create(
            user=maintainer_user, phone_number="+1234567890", country="United States"
        )
        return maintainer_user, maintainer

    def test_period_list_view_shows_correct_counters(self, client, maintainer_with_permissions):
        """Test that the period list view shows correct counter values."""
        maintainer_user, maintainer = maintainer_with_permissions
        client.force_login(maintainer_user)

        # Setup test data
        period1 = Period.objects.create(name="Morning", description="Morning period")
        period2 = Period.objects.create(name="Evening", description="Evening period")

        collection1 = Collection.objects.create(name="Collection 1", enabled=True)
        collection2 = Collection.objects.create(name="Collection 2", enabled=True)

        # Create maintainer-period relationships (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period1)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period2)

        # Period 1: 2 collections, 3 assignments
        pc1_1 = PeriodCollection.objects.create(period=period1, collection=collection1)
        pc1_2 = PeriodCollection.objects.create(period=period1, collection=collection2)
        pa1 = PeriodAssignment.create_with_email(email="a1@example.com", period_collection=pc1_1)
        pa1.save()
        pa2 = PeriodAssignment.create_with_email(email="a2@example.com", period_collection=pc1_1)
        pa2.save()
        pa3 = PeriodAssignment.create_with_email(email="a3@example.com", period_collection=pc1_2)
        pa3.save()

        # Period 2: 1 collection, 1 assignment
        pc2_1 = PeriodCollection.objects.create(period=period2, collection=collection1)
        pa4 = PeriodAssignment.create_with_email(email="a4@example.com", period_collection=pc2_1)
        pa4.save()

        # Make the request
        url = reverse("maintainer:period_list")
        response = client.get(url)

        # Assertions
        assert response.status_code == 200
        periods = response.context["periods"]

        # Convert to list and sort by name for consistent testing
        periods_list = list(periods)
        periods_list.sort(key=lambda p: p.name)

        # Should have 2 periods assigned to this maintainer
        assert len(periods_list) == 2

        # Verify period 1 (Evening comes first alphabetically)
        assert periods_list[0].name == "Evening"
        assert periods_list[0].collection_count == 1
        assert periods_list[0].assignment_count == 1

        # Verify period 2 (Morning)
        assert periods_list[1].name == "Morning"
        assert periods_list[1].collection_count == 2
        assert periods_list[1].assignment_count == 3

    def test_period_list_view_empty_periods(self, client, maintainer_with_permissions):
        """Test period list view with periods that have no collections or assignments."""
        maintainer_user, maintainer = maintainer_with_permissions
        client.force_login(maintainer_user)

        # Create periods with no collections
        period1 = Period.objects.create(name="Empty Period 1", description="No collections")
        period2 = Period.objects.create(name="Empty Period 2", description="No collections")

        # Create maintainer-period relationships (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period1)
        MaintainerPeriod.objects.create(maintainer=maintainer, period=period2)

        url = reverse("maintainer:period_list")
        response = client.get(url)

        assert response.status_code == 200
        periods = list(response.context["periods"])

        # Should have 2 periods assigned to this maintainer
        assert len(periods) == 2

        # Verify all periods have zero counts
        for period in periods:
            assert period.collection_count == 0
            assert period.assignment_count == 0

    def test_period_list_view_queryset_uses_correct_annotations(self, client, maintainer_with_permissions):
        """Test that the view's queryset method produces the expected annotations."""
        from unittest.mock import Mock

        from adoration.maintainer_views import PeriodListView

        maintainer_user, maintainer = maintainer_with_permissions

        # Create test data
        period = Period.objects.create(name="Test Period")
        collection = Collection.objects.create(name="Test Collection", enabled=True)
        pc = PeriodCollection.objects.create(period=period, collection=collection)
        pa = PeriodAssignment.create_with_email(email="test@example.com", period_collection=pc)
        pa.save()

        # Create maintainer-period relationship (required for new functionality)
        from adoration.models import MaintainerPeriod

        MaintainerPeriod.objects.create(maintainer=maintainer, period=period)

        # Get the queryset from the view with mock request
        view = PeriodListView()
        view.request = Mock()
        view.request.user = maintainer_user
        maintainer_user.maintainer = maintainer

        queryset = view.get_queryset()

        # Verify the annotations exist
        annotated_period = queryset.get(name="Test Period")
        assert hasattr(annotated_period, "collection_count")
        assert hasattr(annotated_period, "assignment_count")
        assert annotated_period.collection_count == 1
        assert annotated_period.assignment_count == 1


@pytest.mark.django_db
class TestPeriodCountersEdgeCases:
    """Test edge cases for period counters."""

    def test_period_with_disabled_collection(self):
        """Test that disabled collections are still counted."""
        period = Period.objects.create(name="Test Period")
        collection = Collection.objects.create(name="Disabled Collection", enabled=False)
        pc = PeriodCollection.objects.create(period=period, collection=collection)
        pa = PeriodAssignment.create_with_email(email="test@example.com", period_collection=pc)
        pa.save()

        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Disabled collections should still be counted
        assert annotated_period.collection_count == 1
        assert annotated_period.assignment_count == 1

    def test_period_with_multiple_assignments_same_email_different_collections(self):
        """Test counting assignments when same email is assigned to different collections."""
        period = Period.objects.create(name="Test Period")
        collection1 = Collection.objects.create(name="Collection 1", enabled=True)
        collection2 = Collection.objects.create(name="Collection 2", enabled=True)

        pc1 = PeriodCollection.objects.create(period=period, collection=collection1)
        pc2 = PeriodCollection.objects.create(period=period, collection=collection2)

        # Same email in both collections (different assignments)
        pa1 = PeriodAssignment.create_with_email(email="same@example.com", period_collection=pc1)
        pa1.save()
        pa2 = PeriodAssignment.create_with_email(email="same@example.com", period_collection=pc2)
        pa2.save()

        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Should count as 2 collections and 2 assignments
        assert annotated_period.collection_count == 2
        assert annotated_period.assignment_count == 2

    def test_distinct_counting_prevents_duplicates(self):
        """Test that distinct=True prevents duplicate counting in complex scenarios."""
        period = Period.objects.create(name="Complex Period")
        collection = Collection.objects.create(name="Collection", enabled=True)
        pc = PeriodCollection.objects.create(period=period, collection=collection)

        # Create multiple assignments for the same period collection
        for i in range(5):
            pa = PeriodAssignment.create_with_email(email=f"user{i}@example.com", period_collection=pc)
            pa.save()

        queryset = Period.objects.annotate(
            collection_count=Count("periodcollection", distinct=True),
            assignment_count=Count("periodcollection__periodassignment", distinct=True),
        ).filter(pk=period.pk)

        annotated_period = queryset.get()

        # Should correctly count 1 collection and 5 distinct assignments
        assert annotated_period.collection_count == 1
        assert annotated_period.assignment_count == 5
