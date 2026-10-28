from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.services import normalize_phone


class PhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=16)

    def validate_phone_number(self, value):
        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class VerifySerializer(PhoneSerializer):
    code = serializers.RegexField(r"^\d{4}$", max_length=4)


class InviteSerializer(serializers.Serializer):
    invite_code = serializers.RegexField(r"^[A-Za-z0-9]{6}$", max_length=6)

    def validate_invite_code(self, value):
        return value.upper()


class ProfileSerializer(serializers.Serializer):
    phone_number = serializers.CharField(read_only=True)
    invite_code = serializers.CharField(read_only=True)
    activated_invite_code = serializers.SerializerMethodField()
    invited_phones = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_activated_invite_code(self, obj):
        return obj.invited_by.invite_code if obj.invited_by else None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_invited_phones(self, obj):
        return list(obj.referrals.order_by("id").values_list("phone_number", flat=True))


class RequestCodeResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    expires_in = serializers.IntegerField()


class VerifyResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    token_type = serializers.CharField()
    created = serializers.BooleanField()
    profile = ProfileSerializer()


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()
