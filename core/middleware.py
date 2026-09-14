from django.conf import settings
from django.utils import translation


class LangueUtilisateurMiddleware:
    """Applique la langue du compte quand aucune langue n'est déjà choisie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cookie_langue = settings.LANGUAGE_COOKIE_NAME in request.COOKIES
        if request.user.is_authenticated and not cookie_langue:
            translation.activate(request.user.langue)
        return self.get_response(request)
