from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import as_serializer_error

from .models import Conversation, ConversationStatus, Customer, Message, MessageSender


class CustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "name", "email")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    customer = CustomerSummarySerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "subject", "status", "customer", "created_at", "updated_at")
        read_only_fields = fields


class ConversationQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ConversationStatus.choices, required=False)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "sender", "content", "created_at")
        read_only_fields = fields


class SupportCreateSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = {}
            for name, value in data.items():
                if name not in self.fields:
                    errors[name] = ["This field is not accepted."]
                elif not isinstance(value, str):
                    errors[name] = ["Provide a string."]
            if errors:
                raise serializers.ValidationError(errors)
        return super().to_internal_value(data)

    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        try:
            with transaction.atomic():
                instance.full_clean()
                instance.save(force_insert=True)
        except DjangoValidationError as exc:
            field_names = {
                field.source: field.field_name for field in self.fields.values()
            }
            errors = {
                field_names.get(name, name): errors
                for name, errors in as_serializer_error(exc).items()
            }
            raise serializers.ValidationError(errors) from None
        return instance


class ConversationCreateSerializer(SupportCreateSerializer):
    customer_id = serializers.PrimaryKeyRelatedField(
        source="customer",
        queryset=Customer.objects.all(),
        pk_field=serializers.UUIDField(),
        error_messages={"does_not_exist": "Customer does not exist."},
    )

    class Meta:
        model = Conversation
        fields = ("customer_id", "subject")
        extra_kwargs = {"subject": {"trim_whitespace": False}}


class MessageCreateSerializer(SupportCreateSerializer):
    sender = serializers.ChoiceField(choices=[MessageSender.AGENT])

    class Meta:
        model = Message
        fields = ("sender", "content")
        extra_kwargs = {"content": {"trim_whitespace": False}}

    def create(self, validated_data):
        return super().create(
            {**validated_data, "conversation": self.context["conversation"]}
        )
