from django.contrib.auth import get_user_model
from django.contrib.auth import logout as django_logout
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.services import (
    AttemptsExceededError,
    CooldownError,
    DomainError,
    InvalidReferralError,
    activate_invite_code,
    request_phone_code,
    verify_phone_code,
)

from .serializers import (
    DetailSerializer,
    InviteSerializer,
    PhoneSerializer,
    ProfileSerializer,
    RequestCodeResponseSerializer,
    VerifyResponseSerializer,
    VerifySerializer,
)


class RequestCodeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "sms"

    @extend_schema(
        request=PhoneSerializer,
        responses={202: RequestCodeResponseSerializer, 429: DetailSerializer, 400: DetailSerializer},
        summary="Запросить 4-значный код",
    )
    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ttl = request_phone_code(serializer.validated_data["phone_number"])
        except CooldownError as exc:
            return Response({"detail": str(exc)}, status=429, headers={"Retry-After": str(exc.retry_after)})
        return Response(
            {
                "detail": "Демонстрационный код отправлен (смотрите журнал сервера).",
                "expires_in": ttl,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class VerifyCodeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify"

    @extend_schema(
        request=VerifySerializer,
        responses={200: VerifyResponseSerializer, 400: DetailSerializer, 429: DetailSerializer},
        summary="Подтвердить SMS-код и получить токен",
    )
    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, token, created = verify_phone_code(
                phone=serializer.validated_data["phone_number"],
                code=serializer.validated_data["code"],
            )
        except AttemptsExceededError as exc:
            return Response({"detail": str(exc)}, status=429)
        except DomainError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {
                "token": token,
                "token_type": "Token",
                "created": created,
                "profile": ProfileSerializer(user).data,
            }
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProfileSerializer}, summary="Получить профиль и список приглашённых")
    def get(self, request):
        user = get_user_model().objects.select_related("invited_by").get(pk=request.user.pk)
        return Response(ProfileSerializer(user).data)


class ActivateInviteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=InviteSerializer,
        responses={200: ProfileSerializer, 400: DetailSerializer},
        summary="Активировать чужой инвайт-код (один раз)",
    )
    def post(self, request):
        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            activate_invite_code(request.user, serializer.validated_data["invite_code"])
        except InvalidReferralError as exc:
            return Response({"detail": str(exc)}, status=400)
        user = get_user_model().objects.select_related("invited_by").get(pk=request.user.pk)
        return Response(ProfileSerializer(user).data)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: OpenApiResponse(description="Токен удалён")},
        summary="Аннулировать API-токен",
    )
    def post(self, request):
        request.auth.delete()
        django_logout(request)
        return Response(status=204)
