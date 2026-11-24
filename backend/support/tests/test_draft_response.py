from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from support.models import BODY_MAX_LENGTH, DraftResponse, DraftStatus

from . import postgres_model_tests

pytestmark = postgres_model_tests


def test_multiple_pending_drafts_preserve_history_and_order(message, monkeypatch):
    first = DraftResponse(message=message, content="Earlier proposal")
    first.full_clean()
    first.save()
    updated_at = first.updated_at + timedelta(seconds=1)
    monkeypatch.setattr(timezone, "now", lambda: updated_at)
    second = DraftResponse.objects.create(
        message=message, content="Private response text"
    )
    first.content = "Edited proposal"
    first.save()

    assert list(message.draft_responses.all()) == [second, first]
    assert first.updated_at == updated_at
    assert first.created_at < first.updated_at
    assert second.status == DraftStatus.PENDING
    assert second.reviewed_by is None
    assert second.reviewed_at is None
    assert second.pk.version == 4
    assert str(second) == f"pending draft {second.pk}"


@pytest.mark.parametrize("status", [DraftStatus.APPROVED, DraftStatus.REJECTED])
def test_reviewed_draft_requires_and_preserves_metadata(message, reviewer, status):
    timestamp = timezone.now()
    draft = DraftResponse(
        message=message,
        content="Proposal",
        status=status,
        reviewed_by=reviewer,
        reviewed_at=timestamp,
    )
    draft.full_clean()
    draft.save()
    draft.refresh_from_db()

    assert draft.reviewed_by == reviewer
    assert draft.reviewed_at == timestamp
    assert reviewer.reviewed_support_drafts.get() == draft


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("content", ""),
        ("content", " \t\n"),
        ("content", "x" * (BODY_MAX_LENGTH + 1)),
        ("status", "invalid"),
    ],
)
def test_draft_rejects_invalid_fields(message, field, value):
    values = {"message": message, "content": "Valid proposal", field: value}
    with pytest.raises(ValidationError) as error:
        DraftResponse(**values).full_clean()

    assert field in error.value.message_dict


@pytest.mark.parametrize(
    ("status", "has_reviewer", "has_timestamp"),
    [
        (DraftStatus.PENDING, True, False),
        (DraftStatus.PENDING, False, True),
        (DraftStatus.PENDING, True, True),
        (DraftStatus.APPROVED, False, True),
        (DraftStatus.APPROVED, True, False),
        (DraftStatus.REJECTED, False, True),
        (DraftStatus.REJECTED, True, False),
    ],
)
def test_review_metadata_must_match_status(
    message, reviewer, status, has_reviewer, has_timestamp
):
    draft = DraftResponse(
        message=message,
        content="Proposal",
        status=status,
        reviewed_by=reviewer if has_reviewer else None,
        reviewed_at=timezone.now() if has_timestamp else None,
    )

    with pytest.raises(ValidationError, match="review"):
        draft.full_clean()


def test_reviewed_draft_protects_reviewer_and_cascades_from_message(message, reviewer):
    draft = DraftResponse.objects.create(
        message=message,
        content="Proposal",
        status=DraftStatus.APPROVED,
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )

    with pytest.raises(ProtectedError):
        reviewer.delete()

    message.delete()

    assert not DraftResponse.objects.filter(pk=draft.pk).exists()
    assert type(reviewer).objects.filter(pk=reviewer.pk).exists()
