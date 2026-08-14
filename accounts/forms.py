from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
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
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={'autocomplete' : 'username'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'autocomplete' : 'current-password'}))


class OTPForm(forms.Form):
    code = forms.CharField(min_length=6, max_length=6)

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise forms.ValidationError("Le code doit etre compose de 6 chiffres")
        return code


class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(label="Adresse email")