"""
Tests for Chrome DevTools endpoint handler.

This module tests the Chrome DevTools debugging endpoint that prevents 404 errors
when Chrome DevTools tries to access debugging information.
"""

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestChromeDevToolsHandler:
    """Test cases for Chrome DevTools endpoint handler."""

    def test_chrome_devtools_endpoint_returns_204(self):
        """Test that Chrome DevTools endpoint returns 204 No Content."""
        client = Client()
        response = client.get("/.well-known/appspecific/com.chrome.devtools.json")

        assert response.status_code == 204
        assert response.content == b""

    def test_chrome_devtools_endpoint_accepts_any_method(self):
        """Test that Chrome DevTools endpoint accepts different HTTP methods."""
        client = Client()

        # Test GET
        response = client.get("/.well-known/appspecific/com.chrome.devtools.json")
        assert response.status_code == 204

        # Test POST
        response = client.post("/.well-known/appspecific/com.chrome.devtools.json")
        assert response.status_code == 204

        # Test HEAD
        response = client.head("/.well-known/appspecific/com.chrome.devtools.json")
        assert response.status_code == 204

    def test_chrome_devtools_endpoint_content_type(self):
        """Test that Chrome DevTools endpoint has correct content type."""
        client = Client()
        response = client.get("/.well-known/appspecific/com.chrome.devtools.json")

        assert response.status_code == 204
        # 204 responses typically don't have content-type header
        assert response.get("Content-Type") is None or "text/html" in response.get("Content-Type", "")

    def test_chrome_devtools_endpoint_no_authentication_required(self):
        """Test that Chrome DevTools endpoint doesn't require authentication."""
        # This should work without any authentication
        client = Client()
        response = client.get("/.well-known/appspecific/com.chrome.devtools.json")

        assert response.status_code == 204
        # Should not redirect to login
        assert "login" not in response.get("Location", "")
