from django.urls import path

from . import views

urlpatterns = [
    path("", views.phone_login, name="web_login"),
    path("verify/", views.phone_verify, name="web_verify"),
    path("profile/", views.web_profile, name="web_profile"),
    path("logout/", views.web_logout, name="web_logout"),
]
