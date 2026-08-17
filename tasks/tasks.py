from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Task

User = get_user_model()


@shared_task
def send_daily_task_reminder():

    pending_tasks = (
        Task.objects
        .exclude(status=Task.Status.DONE)
        .select_related("project", "project__user")
    )

    tasks_by_user = {}
    for task in pending_tasks:
        user = task.project.user
        tasks_by_user.setdefault(user, []).append(task.id)

    for user, task_ids in tasks_by_user.items():
        if user.email:
            send_reminder_email_task.delay(user.id, task_ids)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_reminder_email_task(self, user_id, task_ids):

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    tasks = Task.objects.filter(id__in=task_ids).select_related("project")
    message = render_to_string("tasks/emails/daily_reminder.txt", {"username": user.username, "tasks": tasks})
    try:
        send_mail(
            subject="Vos tâches du jour",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)