from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project

from .models import SubTask, Task


class SubTaskModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='amina', email='amina@example.com', password='password123'
        )
        self.project = Project.objects.create(user=self.user, name='Site vitrine')
        self.task = Task.objects.create(project=self.project, title='Préparer les maquettes')

    def test_task_without_subtasks_keeps_existing_status_behavior(self):
        self.task.status = Task.Status.DONE
        self.task.save()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_subtask_has_status_position_and_timestamps(self):
        subtask = SubTask.objects.create(task=self.task, title='Créer la maquette', position=2)
        self.assertEqual(subtask.status, SubTask.Status.NOT_DONE)
        self.assertEqual(subtask.position, 2)
        self.assertIsNotNone(subtask.created_at)
        self.assertIsNotNone(subtask.updated_at)

    def test_task_cannot_be_completed_with_an_unfinished_subtask(self):
        SubTask.objects.create(task=self.task, title='Créer la maquette')
        self.task.status = Task.Status.DONE
        with self.assertRaises(ValidationError):
            self.task.save()

    def test_completing_all_subtasks_completes_the_parent_task(self):
        self.task.status = Task.Status.IN_PROGRESS
        self.task.save()
        subtask = SubTask.objects.create(task=self.task, title='Créer la maquette')
        subtask.status = SubTask.Status.DONE
        subtask.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_unchecking_a_subtask_returns_completed_task_to_in_progress(self):
        subtask = SubTask.objects.create(task=self.task, title='Créer la maquette', status=SubTask.Status.DONE)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)
        subtask.status = SubTask.Status.NOT_DONE
        subtask.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    def test_subtasks_are_ordered_by_position(self):
        second = SubTask.objects.create(task=self.task, title='Deuxième', position=2)
        first = SubTask.objects.create(task=self.task, title='Première', position=1)
        self.assertEqual(list(self.task.subtasks.all()), [first, second])


class SubTaskIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='password123'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='password123'
        )
        project = Project.objects.create(user=self.owner, name='Projet privé')
        self.task = Task.objects.create(project=project, title='Tâche principale')

    def test_task_list_exposes_subtask_progress(self):
        SubTask.objects.create(task=self.task, title='Étape terminée', status=SubTask.Status.DONE)
        SubTask.objects.create(task=self.task, title='Étape restante')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('task_list'))
        self.assertContains(response, '1 / 2 SubTasks')

    def test_owner_can_create_and_toggle_subtask(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('add_subtask', args=[self.task.id]), {'title': 'Créer les modèles'})
        self.assertRedirects(response, reverse('task_detail', args=[self.task.id]))
        subtask = self.task.subtasks.get()
        response = self.client.post(reverse('toggle_subtask', args=[subtask.id]))
        self.assertRedirects(response, reverse('task_detail', args=[self.task.id]))
        subtask.refresh_from_db()
        self.assertEqual(subtask.status, SubTask.Status.DONE)

    def test_task_detail_displays_subtasks(self):
        SubTask.objects.create(task=self.task, title='Créer les modèles')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('task_detail', args=[self.task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Créer les modèles')
        self.assertContains(response, 'Ajouter une SubTask')

    def test_subtask_permissions_follow_task_owner(self):
        subtask = SubTask.objects.create(task=self.task, title='Étape privée')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('task_detail', args=[self.task.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('toggle_subtask', args=[subtask.id])).status_code, 404)

    def test_task_status_endpoint_rejects_done_with_open_subtasks(self):
        SubTask.objects.create(task=self.task, title='Étape ouverte')
        self.client.force_login(self.owner)
        self.client.post(reverse('task_update_status', args=[self.task.id]), {'status': Task.Status.DONE})
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.TODO)


class TaskListDisplayTests(TestCase):
    def test_sidebar_task_page_uses_the_new_task_overview(self):
        user = User.objects.create_user(
            username='amina', email='amina@example.com', password='password123',
        )
        project = Project.objects.create(user=user, name='Site vitrine')
        Task.objects.create(project=project, title='Préparer les maquettes', status=Task.Status.IN_PROGRESS)
        self.client.force_login(user)
        response = self.client.get(reverse('task_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gardez le cap sur vos priorités.')
        self.assertContains(response, 'Préparer les maquettes')
        self.assertContains(response, 'nav-link--active')
        self.assertEqual(response.context['active_nav'], 'tasks')
