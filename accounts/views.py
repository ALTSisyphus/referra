from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import InviteForm, PhoneForm, VerifyForm
from .services import (
    DomainError,
    activate_invite_code,
    request_phone_code,
    verify_phone_code,
)


@require_http_methods(["GET", "POST"])
def phone_login(request):
    if request.user.is_authenticated:
        return redirect("web_profile")
    form = PhoneForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            request_phone_code(form.cleaned_data["phone_number"])
        except DomainError as exc:
            form.add_error(None, str(exc))
        else:
            request.session["pending_phone"] = form.cleaned_data["phone_number"]
            messages.success(request, "Код отправлен в журнал сервера (docker compose logs web).")
            return redirect("web_verify")
    return render(request, "accounts/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def phone_verify(request):
    phone = request.session.get("pending_phone")
    if not phone:
        return redirect("web_login")
    form = VerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user, _, _ = verify_phone_code(phone, form.cleaned_data["code"])
        except DomainError as exc:
            form.add_error(None, str(exc))
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.pop("pending_phone", None)
            messages.success(request, "Авторизация успешна")
            return redirect("web_profile")
    return render(request, "accounts/verify.html", {"form": form, "phone": phone})


@login_required
@require_http_methods(["GET", "POST"])
def web_profile(request):
    form = InviteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            activate_invite_code(request.user, form.cleaned_data["invite_code"])
        except DomainError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Инвайт-код активирован")
            return redirect("web_profile")
    user = get_user_model().objects.select_related("invited_by").get(pk=request.user.pk)
    invited_phones = list(user.referrals.values_list("phone_number", flat=True))
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "member": user,
            "invited_phones": invited_phones,
        },
    )


@login_required
@require_POST
def web_logout(request):
    logout(request)
    return redirect("web_login")
