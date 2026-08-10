from django.shortcuts import redirect, render
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
# Create your views here.

# def registration(request):
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             return render(request, 'template/registration/registration_success.html', {'user': user})
#     else:
#         form = CustomUserCreationForm()
#     return render(request, 'template/registration/registration.html', {'form': form})

# Pourquoi pas :

def registration(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

# QUESTION : Est ce qu'il y a mieux adapte a notre cas ? (la premiere ou la deuxieme ou autre)

# Je passe maintenant au login
def connection(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


# Je passe a la deconection maintenant
def deconnection(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    return redirect('home')


@login_required
def dashboard(request):
    return render(request, 'base.html')