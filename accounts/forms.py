from django import forms

from .services import normalize_phone


class PhoneForm(forms.Form):
    phone_number = forms.CharField(label="Номер телефона", max_length=16)

    def clean_phone_number(self):
        try:
            return normalize_phone(self.cleaned_data["phone_number"])
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


class VerifyForm(forms.Form):
    code = forms.RegexField(label="Код из SMS", regex=r"^\d{4}$", max_length=4)


class InviteForm(forms.Form):
    invite_code = forms.RegexField(label="Чужой инвайт-код", regex=r"^[A-Za-z0-9]{6}$", max_length=6)
