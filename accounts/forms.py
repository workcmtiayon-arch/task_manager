from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Les textes par défaut de Django sont trop techniques pour l'interface.
        for field in self.fields.values():
            field.help_text = ''

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.add('email')

        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            self._update_errors(e)


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label=_('Username'), widget=forms.TextInput(attrs={'autocomplete': 'username'}))
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))


class OTPForm(forms.Form):
    code = forms.CharField(label=_('Verification code'), min_length=6, max_length=6)

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise forms.ValidationError(_('The code must contain 6 digits.'))
        return code


class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(label=_('Email address'))


class ProfileForm(forms.ModelForm):
    """Formulaire limité aux informations qu'un utilisateur peut modifier lui-même."""

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        labels = {
            "username": _("Username"),
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email address"),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        duplicate = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError(_('This email address is already in use.'))
        return email
