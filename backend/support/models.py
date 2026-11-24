import math
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower

BODY_MAX_LENGTH = 10_000
nonblank = RegexValidator(r"\S", "Enter at least one non-whitespace character.")


class ConversationStatus(models.TextChoices):
    OPEN = "open", "Open"
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class MessageSender(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    AGENT = "agent", "Agent"
    SYSTEM = "system", "System"


class AnalysisCategory(models.TextChoices):
    SHIPPING = "shipping", "Shipping"
    REFUND = "refund", "Refund"
    BILLING = "billing", "Billing"
    PRODUCT = "product", "Product"
    ACCOUNT = "account", "Account"
    GENERAL = "general", "General"
    OTHER = "other", "Other"


class Sentiment(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEUTRAL = "neutral", "Neutral"
    NEGATIVE = "negative", "Negative"


class Urgency(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"


class DraftStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


def validate_confidence(value):
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValidationError(
            "Enter a finite score from 0 to 1.", code="invalid_confidence"
        )


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, validators=[nonblank])
    email = models.EmailField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"),
                name="support_customer_name_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(email__regex=r"\S")
                & ~models.Q(email__regex=r"^\s|\s$"),
                name="support_customer_email_trimmed",
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="support_customer_email_ci_uniq",
                violation_error_message="A customer with this email already exists.",
            ),
        ]

    def clean_fields(self, exclude=None):
        if "email" not in (exclude or ()) and isinstance(self.email, str):
            self.email = self.email.strip().lower()
        super().clean_fields(exclude=exclude)

    def __str__(self):
        return f"{self.name} ({self.pk})"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="conversations", db_index=False
    )
    subject = models.CharField(max_length=255, validators=[nonblank])
    status = models.CharField(
        max_length=8,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["status", "-created_at", "-id"],
                name="support_conv_status_created",
            ),
            models.Index(
                fields=["customer", "-created_at", "-id"],
                name="support_conv_cust_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subject__regex=r"\S"),
                name="support_conv_subject_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ConversationStatus.values),
                name="support_conv_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.subject} ({self.pk})"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages", db_index=False
    )
    sender = models.CharField(max_length=8, choices=MessageSender.choices)
    content = models.TextField(
        validators=[nonblank, MaxLengthValidator(BODY_MAX_LENGTH)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at", "id"],
                name="support_msg_conv_created",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sender__in=MessageSender.values),
                name="support_msg_sender_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(content__regex=r"\S"),
                name="support_msg_content_nonblank",
            ),
        ]

    def __str__(self):
        return f"{self.sender} message {self.pk}"


class AIAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(
        Message, on_delete=models.CASCADE, related_name="ai_analysis"
    )
    category = models.CharField(max_length=8, choices=AnalysisCategory.choices)
    sentiment = models.CharField(max_length=8, choices=Sentiment.choices)
    urgency = models.CharField(max_length=6, choices=Urgency.choices)
    confidence = models.FloatField(
        null=True, blank=True, validators=[validate_confidence]
    )
    reason = models.TextField(blank=True)
    model_name = models.CharField(max_length=200, validators=[nonblank])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=AnalysisCategory.values),
                name="support_analysis_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(sentiment__in=Sentiment.values),
                name="support_analysis_sentiment_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(urgency__in=Urgency.values),
                name="support_analysis_urgency_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__isnull=True)
                | models.Q(confidence__gte=0.0, confidence__lte=1.0),
                name="support_analysis_confidence_range",
            ),
            models.CheckConstraint(
                condition=models.Q(model_name__regex=r"\S"),
                name="support_analysis_model_nonblank",
            ),
        ]

    def clean(self):
        super().clean()
        if self.message_id is None:
            return
        try:
            sender = self.message.sender
        except Message.DoesNotExist:
            return  # Field validation reports the missing reference.
        if sender != MessageSender.CUSTOMER:
            raise ValidationError(
                {"message": "Analysis requires a customer-authored message."}
            )

    def __str__(self):
        return f"{self.category} analysis for message {self.message_id}"


class DraftResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="draft_responses",
        db_index=False,
    )
    content = models.TextField(
        validators=[nonblank, MaxLengthValidator(BODY_MAX_LENGTH)]
    )
    status = models.CharField(
        max_length=8, choices=DraftStatus.choices, default=DraftStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_support_drafts",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["message", "-created_at", "-id"],
                name="support_draft_msg_created",
            ),
            models.Index(
                fields=["-created_at", "-id"],
                condition=models.Q(status=DraftStatus.PENDING),
                name="support_draft_pending_created",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(content__regex=r"\S"),
                name="support_draft_content_nonblank",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status=DraftStatus.PENDING,
                    reviewed_by__isnull=True,
                    reviewed_at__isnull=True,
                )
                | models.Q(
                    status__in=[DraftStatus.APPROVED, DraftStatus.REJECTED],
                    reviewed_by__isnull=False,
                    reviewed_at__isnull=False,
                ),
                name="support_draft_review_consistent",
            ),
        ]

    def clean(self):
        super().clean()
        if self.status == DraftStatus.PENDING:
            if self.reviewed_by_id is not None or self.reviewed_at is not None:
                raise ValidationError("A pending draft must have no review metadata.")
        elif self.status in (DraftStatus.APPROVED, DraftStatus.REJECTED):
            if self.reviewed_by_id is None or self.reviewed_at is None:
                raise ValidationError(
                    "A reviewed draft requires a reviewer and a timestamp."
                )

    def __str__(self):
        return f"{self.status} draft {self.pk}"
