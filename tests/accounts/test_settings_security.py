from django.conf import settings
from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured

from config.settings import validate_production_database_settings


class SecuritySettingsTests(SimpleTestCase):
    def test_debug_is_disabled_by_default(self):
        self.assertFalse(settings.DEBUG)

    def test_secret_key_is_not_the_insecure_placeholder(self):
        self.assertNotEqual(settings.SECRET_KEY, "SECRET_KEY")
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50)

    def test_authentication_cookies_are_secure(self):
        self.assertEqual(settings.SESSION_COOKIE_SECURE, settings.DEPLOYMENT_ENV == "production")
        self.assertEqual(settings.CSRF_COOKIE_SECURE, settings.DEPLOYMENT_ENV == "production")
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")

    def test_content_type_sniffing_is_disabled(self):
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)

    def test_production_database_rejects_a_missing_postgres_host(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_database_settings("", "s" * 40)

    def test_production_database_rejects_development_passwords(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_database_settings("postgres", "task_manager_dev_password")

    def test_production_database_accepts_a_long_private_password(self):
        validate_production_database_settings("postgres", "p" * 40)
