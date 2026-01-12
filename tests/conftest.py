"""
Pytest configuration and fixtures for Django testing.
"""

import os
import sys
from pathlib import Path

import pytest

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Configure Django settings for testing
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

# Setup Django
import django

django.setup()


@pytest.fixture
def test_client():
    """Django test client fixture."""

    from django.test import Client

    return Client()


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    from django.contrib.auth.models import User

    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def maintainer_user(db):
    """Create a maintainer user."""
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="maintainer",
        email="maintainer@example.com",
        password="maintainerpass123",
        first_name="Maintainer",
        last_name="User",
    )


@pytest.fixture
def period(db):
    """Create a test period."""
    from adoration.models import Period

    return Period.objects.create(name="Morning Prayer", description="6:00 AM - 7:00 AM Morning adoration")


@pytest.fixture
def period2(db):
    """Create a second test period."""
    from adoration.models import Period

    return Period.objects.create(name="Evening Prayer", description="6:00 PM - 7:00 PM Evening adoration")


@pytest.fixture
def collection(db):
    """Create a test collection."""
    from adoration.models import Collection

    return Collection.objects.create(name="Weekly Adoration", description="Weekly adoration schedule", enabled=True)


@pytest.fixture
def disabled_collection(db):
    """Create a disabled test collection."""
    from adoration.models import Collection

    return Collection.objects.create(
        name="Disabled Collection",
        description="This collection is disabled",
        enabled=False,
    )


@pytest.fixture
def maintainer(db, maintainer_user):
    """Create a test maintainer."""
    from adoration.models import Maintainer

    return Maintainer.objects.create(user=maintainer_user, phone_number="+1234567890", country="United States")


@pytest.fixture
def collection_maintainer(db, collection, maintainer):
    """Create a collection maintainer relationship."""
    from adoration.models import CollectionMaintainer

    return CollectionMaintainer.objects.create(collection=collection, maintainer=maintainer)


@pytest.fixture
def period_collection(db, period, collection):
    """Create a period collection relationship."""
    from adoration.models import PeriodCollection

    return PeriodCollection.objects.create(period=period, collection=collection)


@pytest.fixture
def period_collection2(db, period2, collection):
    """Create a second period collection relationship."""
    from adoration.models import PeriodCollection

    return PeriodCollection.objects.create(period=period2, collection=collection)


@pytest.fixture
def config(db):
    """Get or create test configuration."""
    from adoration.models import Config

    # Try to get existing config from migration first
    try:
        return Config.objects.get(name=Config.DefaultValues.ASSIGNMENT_LIMIT)
    except Config.DoesNotExist:
        # Fallback to creating if it doesn't exist
        return Config.objects.create(
            name=Config.DefaultValues.ASSIGNMENT_LIMIT,
            value="5",
            description="Maximum assignments per period",
        )


@pytest.fixture
def collection_config(db, collection):
    """Create collection-specific configuration."""
    from adoration.models import CollectionConfig

    return CollectionConfig.objects.create(
        collection=collection,
        name=CollectionConfig.ConfigKeys.ASSIGNMENT_LIMIT,
        value="3",
        description="Collection-specific assignment limit",
    )


@pytest.fixture
def period_assignment(db, period_collection):
    """Create a test period assignment."""
    from adoration.models import PeriodAssignment

    return PeriodAssignment.create_with_email(email="participant@example.com", period_collection=period_collection)


@pytest.fixture
def complete_setup(
    db,
    collection,
    period,
    period2,
    maintainer,
    collection_maintainer,
    period_collection,
    period_collection2,
    config,
):
    """Complete test setup with all related objects."""
    return {
        "collection": collection,
        "period": period,
        "period2": period2,
        "maintainer": maintainer,
        "collection_maintainer": collection_maintainer,
        "period_collection": period_collection,
        "period_collection2": period_collection2,
        "config": config,
    }


@pytest.fixture
def assignment_form_data():
    """Valid form data for period assignment."""
    return {
        "attendant_name": "John Doe",
        "attendant_email": "john@example.com",
        "attendant_phone_number": "+1234567890",
    }


@pytest.fixture
def mail_outbox():
    """Access Django's test mail outbox."""
    from django.core import mail

    mail.outbox = []
    return mail.outbox
