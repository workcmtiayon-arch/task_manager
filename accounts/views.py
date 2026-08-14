from .forms import CustomUserCreationForm, CustomAuthenticationForm, ForgotPasswordEmailForm, OTPForm
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect, render
from .models import EmailOTP
from .tasks import send_otp_email_task, send_registration_alert_email_task


# Create your views here.
User = get_user_model()

def registration(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            existing = User.objects.filter(email__iexact=email).first()

            if existing:
                send_registration_alert_email_task.delay(existing.email)
            else:
                user = form.save(commit=False)
                user.is_active = False
                user.email = email
                user.save()
                _, code = EmailOTP.generate_for(user, EmailOTP.Purpose.REGISTER)
                send_otp_email_task.delay(user.id, code, EmailOTP.Purpose.REGISTER)
                request.session['pending_user_id'] = user.id
            return redirect('verify-otp')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})




def verify_otp(request):
    user_id = request.session.get('pending_user_id')
    error = None

    if request.method == "POST":
        form=OTPForm(request.POST)
        if form.is_valid():
            otp = None
            if user_id:
                otp = (
                    EmailOTP.objects.filter(
                        user_id=user_id, 
                        purpose=EmailOTP.Purpose.REGISTER, is_used=False
                    )
                    .order_by('-created_at')
                    .first()
                )
            if otp and otp.check_email(form.cleaned_data['code']):
                User.objects.filter(pk=user_id).update(is_active=True, is_email_verified=True)
                request.session.pop('pending_user_id', None)
                messages.success(request, "Adresse e-mail verifiee. Vous pouvez vous connecter")
                return redirect('login')

            error = "Code invalide ou expire"

    else:
        form=OTPForm()

    return render(request, "accounts/verify_otp.html", {'form': form, "error": error})




def resend_otp(request):
    user_id = request.session.get('pending_user_id')
    if user_id:
        user = User.objects.filter(pk=user_id, is_active=False).first()
        if user:
            otp, code = EmailOTP.generate_for(user, EmailOTP.Purpose.REGISTER)
            send_otp_email_task.delay(user.id, code, EmailOTP.Purpose.REGISTER)
    messages.info(request, "Si une demande est en attente, un nouveau code vient d'etre envoye")
    return redirect('verify-otp')




# mdp oublie : demande de l'email
def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                otp, code = EmailOTP.generate_for(user, EmailOTP.Purpose.PASSWORD_RESET)
                send_otp_email_task.delay(user.id, code, EmailOTP.Purpose.PASSWORD_RESET)
                request.session['reset_user_id'] = user.id
                messages.info(request, "Si cette adresse est associee a un compte un code a ete envoye")
            return redirect('verify-reset-otp')
    else:
        form = ForgotPasswordEmailForm()
    return render(request, 'accounts/forgot_password.html', {'form': form})

# mdp oublie : verification du code
def verify_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    error = None

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = None
            if user_id:
                otp =(
                    EmailOTP.objects.filter(
                        user_id=user_id,
                        purpose=EmailOTP.Purpose.PASSWORD_RESET,
                        is_used=False,
                    )
                    .order_by('-created_at')
                    .first()
                )
            if otp and otp.check_email(form.cleaned_data['code']):
                request.session['reset_verified_user_id'] = user_id
                request.session.pop('reset_user_id', None)
                return redirect('reset-password')
            error = "Code Invalide ou expire"

    else:
        form = OTPForm()

    return render(request, 'accounts/verify_reset_otp.html', {'form': form, 'error': error})


# mot de passe oublie : nouveau mot de passe
def reset_password(request):
    user_id = request.session.get('reset_verified_user_id')
    if not user_id:
        return redirect('forgot-password')
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            request.session.pop('reset_verified_user_id', None)
            messages.success(request, "Mot de passe reinitialise. Tu peux te connecter...")
            return redirect('login')

    else:
        form = SetPasswordForm(user)

    return render(request, 'accounts/reset_password.html', {'form' : form})

# connexion
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
def deconnexion(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    return redirect('home')


@login_required
def dashboard(request):
    return render(request, 'base.html')