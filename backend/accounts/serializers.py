from collections.abc import Mapping

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150, trim_whitespace=False, write_only=True
    )
    password = serializers.CharField(
        max_length=4096, trim_whitespace=False, write_only=True
    )

    def to_internal_value(self, data):
        if (
            not isinstance(data, Mapping)
            or set(data) != set(self.fields)
            or any(not isinstance(value, str) for value in data.values())
        ):
            raise serializers.ValidationError(
                {"detail": "Submit only a username and password."}
            )
        return super().to_internal_value(data)

    def validate_username(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value
