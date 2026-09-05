from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class Project(models.Model):
    class Complexity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    class TemporalStatus(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        OVERDUE = "OVERDUE", "Overdue"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    planned_start_date = models.DateField(default=timezone.localdate)
    planned_duration_days = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Planned duration in calendar days.",
    )
    complexity = models.CharField(
        max_length=10,
        choices=Complexity.choices,
        default=Complexity.MEDIUM,
    )
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    @property
    def planned_end_date(self):
        """Return the inclusive planned end date without storing a duplicate."""
        return self.planned_start_date + timedelta(days=self.planned_duration_days - 1)

    @property
    def created_at(self):
        """Compatibility alias using the conventional timestamp spelling."""
        return self.create_at

    @property
    def updated_at(self):
        """Compatibility alias using the conventional timestamp spelling."""
        return self.update_at

    @property
    def is_completed(self):
        tasks = self.task_set.all()
        return tasks.exists() and not tasks.exclude(status="DONE").exists()

    @property
    def overdue_task_count(self):
        today = timezone.localdate()
        return self.task_set.filter(due_date__lt=today).exclude(status="DONE").count()

    @property
    def temporal_status(self):
        if self.is_completed:
            return self.TemporalStatus.COMPLETED
        today = timezone.localdate()
        if today < self.planned_start_date:
            return self.TemporalStatus.UPCOMING
        if today > self.planned_end_date:
            return self.TemporalStatus.OVERDUE
        return self.TemporalStatus.IN_PROGRESS

    def __str__(self):
        return self.name

    def clean(self):
        if self.planned_duration_days is not None and self.planned_duration_days < 1:
            raise ValidationError({'planned_duration_days': 'Duration must be at least one day.'})
