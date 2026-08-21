from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    ForgotPasswordEmailForm,
    OTPForm,
    ProfileForm,
)
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
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
    # Imports locaux pour garder les applications découplées et ne rien changer au chat.
    from projects.models import Project
    from projects.forms import ProjectForm
    from tasks.models import Task
    from chat.models import Conversation, ConversationMember

    is_admin = request.user.is_superuser or request.user.role == User.Role.ADMIN
    if is_admin:
        projects = Project.objects.all()
        tasks = Task.objects.all()
        conversation_count = Conversation.objects.count()
        user_count = User.objects.count()
        active_user_count = User.objects.filter(is_active=True).count()
    else:
        projects = Project.objects.filter(user=request.user)
        tasks = Task.objects.filter(project__user=request.user)
        conversation_count = (
            ConversationMember.objects.filter(user=request.user, left_at__isnull=True)
            .values("conversation_id")
            .distinct()
            .count()
        )
        user_count = None
        active_user_count = None

    project_count = projects.count()
    completed_project_count = (
        projects.annotate(
            task_count=Count("task"),
            remaining_task_count=Count("task", filter=~Q(task__status=Task.Status.DONE)),
        )
        .filter(task_count__gt=0, remaining_task_count=0)
        .count()
    )
    incomplete_project_count = project_count - completed_project_count
    completed_project_percentage = (
        round(completed_project_count * 100 / project_count) if project_count else 0
    )
    task_count = tasks.count()
    completed_task_count = tasks.filter(status=Task.Status.DONE).count()
    in_progress_task_count = tasks.filter(status=Task.Status.IN_PROGRESS).count()
    todo_task_count = tasks.filter(status=Task.Status.TODO).count()
    completed_percentage = round(completed_task_count * 100 / task_count) if task_count else 0
    remaining_percentage = 100 - completed_percentage if task_count else 0

    return render(request, "accounts/dashboard.html", {
        "active_nav": "dashboard",
        "is_dashboard_admin": is_admin,
        "user_count": user_count,
        "active_user_count": active_user_count,
        "project_count": project_count,
        "completed_project_count": completed_project_count,
        "incomplete_project_count": incomplete_project_count,
        "completed_project_percentage": completed_project_percentage,
        "conversation_count": conversation_count,
        "task_count": task_count,
        "completed_task_count": completed_task_count,
        "in_progress_task_count": in_progress_task_count,
        "todo_task_count": todo_task_count,
        "completed_percentage": completed_percentage,
        "remaining_percentage": remaining_percentage,
        "project_form": ProjectForm(),
    })


def is_platform_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN)


@login_required
def user_list(request):
    if not is_platform_admin(request.user):
        return HttpResponseForbidden("Cette page est réservée aux administrateurs.")

    users = User.objects.all().order_by("-date_joined", "username")
    return render(request, "accounts/user_list.html", {
        "users": users,
        "active_nav": "users",
    })


@login_required
def toggle_user_status(request, user_id):
    if not is_platform_admin(request.user):
        return HttpResponseForbidden("Cette action est réservée aux administrateurs.")
    if request.method != "POST":
        return redirect("user_list")

    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
    elif user.is_superuser:
        messages.error(request, "Le compte super-administrateur ne peut pas être modifié ici.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        state = "activé" if user.is_active else "désactivé"
        messages.success(request, f"Le compte de {user.username} a été {state}.")
    return redirect("user_list")


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vos informations de profil ont été mises à jour.")
        return redirect("profile")
    return render(request, "profile/profile.html", {"form": form, "active_nav": "profile"})


@login_required
def system_settings(request):
    if not is_platform_admin(request.user):
        return HttpResponseForbidden("Cette page est réservée aux administrateurs.")
    return render(request, "accounts/system_settings.html", {"active_nav": "settings"})
