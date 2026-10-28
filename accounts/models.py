"""Custom user and one active OTP challenge per phone number."""

import secrets
import string

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import IntegrityError, models, transaction
from django.utils import timezone

INVITE_ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code():
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(6))


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        if "invite_code" in extra_fields:
            raise ValueError("Invite code is managed by the application")
        for _ in range(15):
            user = self.model(
                phone_number=phone_number,
                invite_code=generate_invite_code(),
                **extra_fields,
            )
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            try:
                with transaction.atomic(using=self._db):
                    user.save(using=self._db, force_insert=True)
                return user
            except IntegrityError:
                if self.filter(phone_number=phone_number).exists():
                    raise
        raise RuntimeError("Failed to generate a unique invite code")

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser requires is_staff=True and is_superuser=True")
        if not password:
            raise ValueError("Superuser password is required")
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField("Номер телефона", max_length=16, unique=True)
    invite_code = models.CharField("Личный инвайт-код", max_length=6, unique=True, editable=False)
    invited_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
        verbose_name="Пригласивший",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["id"]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.phone_number


class PhoneChallenge(models.Model):
    phone_number = models.CharField(max_length=16, unique=True)
    code_digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Challenge for {self.phone_number}"
