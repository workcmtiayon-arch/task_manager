from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tasks.models import Task

from .forms import ProjectForm
from .models import Project


class ProjectDomainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='nadia', email='nadia@example.com', password='password123'
        )

    def project(self, **kwargs):
        return Project.objects.create(
            user=self.user,
            name=kwargs.pop('name', 'Portfolio'),
            planned_start_date=kwargs.pop('planned_start_date', date(2026, 10, 1)),
            planned_duration_days=kwargs.pop('planned_duration_days', 61),
            **kwargs,
        )

    def test_project_stores_owner_and_planning_data(self):
        project = self.project()
        self.assertEqual(project.user, self.user)
        self.assertEqual(project.planned_end_date, date(2026, 11, 30))
        self.assertEqual(project.complexity, Project.Complexity.MEDIUM)

    def test_duration_must_be_positive(self):
        form = ProjectForm(data={
            'name': 'Invalid',
            'description': '',
            'planned_start_date': '2026-10-01',
            'planned_duration_days': 0,
            'complexity': 'HIGH',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('planned_duration_days', form.errors)

    @patch('projects.models.timezone.localdate', return_value=date(2026, 9, 5))
    def test_temporal_status_is_upcoming(self, mocked_today):
        self.assertEqual(self.project().temporal_status, Project.TemporalStatus.UPCOMING)

    @patch('projects.models.timezone.localdate', return_value=date(2026, 10, 15))
    def test_temporal_status_is_in_progress(self, mocked_today):
        self.assertEqual(self.project().temporal_status, Project.TemporalStatus.IN_PROGRESS)

    @patch('projects.models.timezone.localdate', return_value=date(2026, 12, 1))
    def test_temporal_status_is_overdue(self, mocked_today):
        self.assertEqual(self.project().temporal_status, Project.TemporalStatus.OVERDUE)

    @patch('projects.models.timezone.localdate', return_value=date(2026, 10, 15))
    def test_completed_status_requires_all_tasks_done(self, mocked_today):
        project = self.project(planned_duration_days=61)
        Task.objects.create(project=project, title='Design', status=Task.Status.DONE)
        self.assertEqual(project.temporal_status, Project.TemporalStatus.COMPLETED)

    @patch('projects.models.timezone.localdate', return_value=date(2026, 10, 15))
    def test_late_task_does_not_make_project_overdue(self, mocked_today):
        project = self.project(planned_duration_days=61)
        Task.objects.create(project=project, title='Backend', due_date=date(2026, 10, 10))
        self.assertEqual(project.temporal_status, Project.TemporalStatus.IN_PROGRESS)
        self.assertEqual(project.overdue_task_count, 1)


class ProjectAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='password123'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='password123'
        )

    def test_creation_assigns_authenticated_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('project_add'), {
            'name': 'Owned project',
            'description': '',
            'planned_start_date': '2026-10-01',
            'planned_duration_days': 10,
            'complexity': 'HIGH',
        })
        self.assertRedirects(response, reverse('project_list'))
        self.assertEqual(Project.objects.get(name='Owned project').user, self.owner)

    def test_project_detail_is_isolated_by_owner(self):
        project = Project.objects.create(user=self.owner, name='Private')
        self.client.force_login(self.other)
        response = self.client.get(reverse('project_detail', args=[project.id]))
        self.assertEqual(response.status_code, 404)

    def test_project_list_requires_authentication(self):
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 302)


class ProjectListDisplayTests(TestCase):
    def test_project_list_uses_the_project_overview(self):
        user = User.objects.create_user(
            username='cssuser', email='css@example.com', password='SecurePass123!'
        )
        Project.objects.create(user=user, name='Plateforme web')
        self.client.force_login(user)
        response = self.client.get(reverse('project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Donnez vie à vos idées, projet par projet.')
        self.assertContains(response, 'Plateforme web')
        self.assertEqual(response.context['active_nav'], 'projects')
        self.assertContains(response, 'Upcoming')

    def test_project_list_includes_projects_css_and_static_accessible(self):
        user = User.objects.create_user(
            username='staticuser', email='static@example.com', password='SecurePass123!'
        )
        Project.objects.create(user=user, name='CSS Test')
        self.client.force_login(user)
        response = self.client.get(reverse('project_list'))
        self.assertContains(response, '/static/css/projects.css')
        self.assertEqual(self.client.get('/static/css/projects.css').status_code, 200)
