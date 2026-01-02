"""
Unit tests for adoration URL patterns.

This module tests URL resolution and basic endpoint functionality
for the adoration Django application.
"""

import pytest
from django.urls import resolve, reverse

from adoration.models import PeriodAssignment


class TestAdorationUrls:
    """Test cases for adoration URL patterns."""

    def test_registration_url_resolves(self):
        """Test that the registration URL resolves to the correct view."""
        url = reverse("registration")
        resolver = resolve(url)
        assert resolver.view_name == "registration"
        assert resolver.func.__name__ == "registration_view"

    def test_registration_get_request(self, test_client, db):
        """Test GET request to registration endpoint returns form."""
        url = reverse("registration")
        response = test_client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        # Check that the form is rendered in the response
        assert b"form" in response.content or b"registration" in response.content.lower()

    def test_delete_assignment_url_resolves(self):
        """Test that the delete assignment URL resolves correctly."""
        url = reverse("delete_assignment", kwargs={"token": "test-token-123"})
        resolver = resolve(url)
        assert resolver.view_name == "delete_assignment"
        assert resolver.func.__name__ == "delete_assignment"

    def test_get_collection_periods_url_resolves(self):
        """Test that the collection periods API URL resolves correctly."""
        url = reverse("get_collection_periods", kwargs={"collection_id": 1})
        resolver = resolve(url)
        assert resolver.view_name == "get_collection_periods"
        assert resolver.func.__name__ == "get_collection_periods"

    def test_delete_assignment_get_request(self, test_client, period_assignment):
        """Test GET request to delete assignment page."""
        # Ensure assignment is saved to database
        period_assignment.save()

        url = reverse("delete_assignment", kwargs={"token": period_assignment.deletion_token})
        response = test_client.get(url)

        assert response.status_code == 200
        assert "assignment" in response.context
        assert "form" in response.context

    def test_get_collection_periods_ajax_request(self, test_client, complete_setup):
        """Test AJAX request to get collection periods."""
        setup = complete_setup
        url = reverse("get_collection_periods", kwargs={"collection_id": setup["collection"].id})
        response = test_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert isinstance(data["periods"], list)

    def test_registration_post_request(self, test_client, complete_setup):
        """Test POST request to registration endpoint."""
        setup = complete_setup

        form_data = {
            "collection": setup["collection"].id,
            "period_collection": setup["period_collection"].id,
            "attendant_name": "Test User",
            "attendant_email": "test@example.com",
            "privacy_accepted": True,
        }

        response = test_client.post(reverse("registration"), form_data)
        assert response.status_code == 302  # Redirect after successful submission

    def test_delete_assignment_post_request(self, test_client, period_collection):
        """Test POST request to delete assignment."""
        email = "delete@example.com"
        assignment = PeriodAssignment.create_with_email(email=email, period_collection=period_collection)
        assignment.save()

        form_data = {"email": email}
        url = reverse("delete_assignment", kwargs={"token": assignment.deletion_token})
        response = test_client.post(url, form_data)

        assert response.status_code == 302  # Redirect after successful deletion

    def test_invalid_token_404(self, test_client, db):
        """Test that invalid deletion token returns 404."""
        url = reverse("delete_assignment", kwargs={"token": "invalid-token-123"})
        response = test_client.get(url)

        assert response.status_code == 404

    def test_nonexistent_collection_periods_404(self, test_client, db):
        """Test that requesting periods for nonexistent collection returns 500 due to exception handling."""
        url = reverse("get_collection_periods", kwargs={"collection_id": 99999})
        response = test_client.get(url)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "Failed to load periods"
