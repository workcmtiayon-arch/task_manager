from django.conf import settings
from django.test import SimpleTestCase


class SecuritySettingsTests(SimpleTestCase):
    def test_debug_is_disabled_by_default(self):
        self.assertFalse(settings.DEBUG)

    def test_secret_key_is_not_the_insecure_placeholder(self):
        self.assertNotEqual(settings.SECRET_KEY, "SECRET_KEY")
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50)

    def test_authentication_cookies_are_secure(self):
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")
