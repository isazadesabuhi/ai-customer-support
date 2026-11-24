from datetime import timedelta
from uuid import UUID

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from support.models import Customer

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_customer_normalizes_email_and_sets_uuid_and_timestamps(monkeypatch):
    customer = Customer(name="Example Name", email="  Example@Example.Test  ")
    assert isinstance(customer.pk, UUID)
    assert customer.pk.version == 4

    customer.full_clean()
    customer.save()

    assert Customer.objects.get(pk=customer.pk).email == "example@example.test"
    assert timezone.is_aware(customer.created_at)
    assert customer.updated_at >= customer.created_at
    assert str(customer) == f"Example Name ({customer.pk})"

    created_at = customer.created_at
    updated_at = customer.updated_at + timedelta(seconds=1)
    monkeypatch.setattr(timezone, "now", lambda: updated_at)
    customer.name = "Updated Name"
    customer.save()
    customer.refresh_from_db()

    assert customer.created_at == created_at
    assert customer.updated_at == updated_at


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", " \t\n"),
        ("name", "n" * 201),
        ("email", ""),
        ("email", "malformed"),
        ("email", "x" * 250 + "@example.test"),
    ],
)
def test_customer_rejects_invalid_fields(field, value):
    values = {"name": "Valid Name", "email": "person@example.test", field: value}

    with pytest.raises(ValidationError) as error:
        Customer(**values).full_clean()

    assert field in error.value.message_dict


@pytest.mark.parametrize("email", ["customer@example.test", " CUSTOMER@EXAMPLE.TEST "])
def test_customer_rejects_duplicate_email_during_validation(customer, email):
    with pytest.raises(
        ValidationError, match="A customer with this email already exists"
    ):
        Customer(name="Another Customer", email=email).full_clean()
