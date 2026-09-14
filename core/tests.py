from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccueilInternationaliseTests(TestCase):
    def test_accueil_est_en_francais_par_defaut(self):
        reponse = self.client.get(reverse('home'))

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'Organisez vos projets')

    def test_selection_anglaise_est_appliquee_et_persistee(self):
        utilisateur = User.objects.create_user(
            username='langue-user',
            email='langue@example.com',
            password='SecurePass123!',
        )
        self.client.force_login(utilisateur)

        reponse = self.client.post(reverse('changer_langue'), {
            'langue': 'en',
            'suivant': reverse('home'),
        })

        self.assertRedirects(reponse, reverse('home'))
        utilisateur.refresh_from_db()
        self.assertEqual(utilisateur.langue, 'en')
        page_anglaise = self.client.get(reverse('home'))
        self.assertContains(page_anglaise, 'Organize your projects')

# Create your tests here.
