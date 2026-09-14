from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme

# Create your views here.

def home(request):
    return render(request, 'home.html')# test


def changer_langue(request):
    langue = request.POST.get('langue', '')
    langues_disponibles = {code for code, nom in settings.LANGUAGES}

    if request.method == 'POST' and langue in langues_disponibles:
        translation.activate(langue)
        if request.user.is_authenticated and request.user.langue != langue:
            request.user.langue = langue
            request.user.save(update_fields=['langue'])

    destination = request.POST.get('suivant') or request.META.get('HTTP_REFERER')
    if not destination or not url_has_allowed_host_and_scheme(
        destination, allowed_hosts={request.get_host()}
    ):
        destination = reverse('home')
    reponse = redirect(destination)
    if request.method == 'POST' and langue in langues_disponibles:
        reponse.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            langue,
            max_age=settings.LANGUAGE_COOKIE_AGE,
        )
    return reponse
