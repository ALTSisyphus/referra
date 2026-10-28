from django.urls import path

from .views import (
    ActivateInviteView,
    LogoutView,
    ProfileView,
    RequestCodeView,
    VerifyCodeView,
)

urlpatterns = [
    path("auth/request-code/", RequestCodeView.as_view(), name="request-code"),
    path("auth/verify-code/", VerifyCodeView.as_view(), name="verify-code"),
    path("auth/logout/", LogoutView.as_view(), name="api-logout"),
    path("profile/", ProfileView.as_view(), name="api-profile"),
    path("profile/activate-invite/", ActivateInviteView.as_view(), name="activate-invite"),
]
