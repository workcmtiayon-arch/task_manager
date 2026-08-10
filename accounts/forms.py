from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={'autocomplete' : 'username'}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'autocomplete' : 'current-password'}))

# Pourquoi on a pas fait plutot de cette maniere la ? :

# class CustonUserCreationForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password1', 'password2', 'role']




# Ou bien de cette maniere la ? :

# class CustonUserCreationForm(UserCreationForm):
#     password1 = forms.CharField(
#         label='Password',
#         strip=False,
#         widget= forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
#         help_text='Enter a strong password.',
#     )
#     password2 = forms.CharField(
#         label='Password confirmation',
#         widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
#         strip=False,
#         help_text='Enter the same password as before, for verification.',
#     )

#     class Meta(UserCreationForm.Meta):
#         fields = UserCreationForm.Meta.fields + ("password1", "password2")


# C'est quoi la meilleure facon de faire des trois ?