from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from projects.models import Project

# Create your models here.

class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    class Status(models.TextChoices):
        TODO = "TODO", "À faire"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        DONE = "DONE", "Terminée"
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def clean(self):
        if self.pk and self.subtasks.exists():
            expected_status = (
                self.Status.DONE
                if not self.subtasks.filter(status=SubTask.Status.NOT_DONE).exists()
                else self.Status.IN_PROGRESS
            )
            if self.status != expected_status:
                raise ValidationError({
                    'status': 'Le statut est géré automatiquement par les SubTasks.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def sync_status_from_subtasks(self):
        """Keep the parent status consistent after a subtask change."""
        if not self.pk or not self.subtasks.exists():
            return
        has_unfinished = self.subtasks.filter(status=SubTask.Status.NOT_DONE).exists()
        next_status = self.Status.IN_PROGRESS if has_unfinished else self.Status.DONE
        if self.status != next_status:
            self.status = next_status
            type(self).objects.filter(pk=self.pk).update(status=next_status)


class SubTask(models.Model):
    class Status(models.TextChoices):
        NOT_DONE = 'NOT_DONE', 'Non terminée'
        DONE = 'DONE', 'Terminée'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOT_DONE)
    position = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'created_at', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['task', 'position'], name='unique_subtask_position_per_task'),
        ]
        indexes = [
            models.Index(fields=['task', 'position'], name='task_subtask_position_idx'),
            models.Index(fields=['task', 'status'], name='task_subtask_status_idx'),
        ]

    def clean(self):
        if self.task_id and self.task.project_id is None:
            raise ValidationError({'task': 'A subtask must belong to a project task.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.task.sync_status_from_subtasks()

    def delete(self, *args, **kwargs):
        task = self.task
        result = super().delete(*args, **kwargs)
        task.sync_status_from_subtasks()
        return result

    def __str__(self):
        return self.title
