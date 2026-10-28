"""Read-only user administration; account creation occurs through OTP verification."""

from django.contrib import admin

from .models import PhoneChallenge, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_number", "invite_code", "invited_by", "is_staff")
    search_fields = ("phone_number", "invite_code")
    ordering = ("id",)
    readonly_fields = ("phone_number", "invite_code", "invited_by", "is_staff", "is_active", "date_joined")
    fields = ("phone_number", "invite_code", "invited_by", "is_staff", "is_active", "date_joined")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PhoneChallenge)
class PhoneChallengeAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "expires_at", "attempts", "consumed_at")
    search_fields = ("phone_number",)
    readonly_fields = ("phone_number", "code_digest", "expires_at", "last_sent_at", "attempts", "consumed_at")
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
