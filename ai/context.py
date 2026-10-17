"""Build the smallest safe project context for an AI request."""

from django.db.models import Prefetch

from projects.models import Project
from tasks.models import SubTask, Task


def build_user_context(user, project_id=None):
    """Return only projects owned by ``user`` and their tasks/subtasks."""
    task_queryset = Task.objects.order_by("pk")[:30].prefetch_related(
        Prefetch("subtasks", queryset=SubTask.objects.order_by("pk")[:20], to_attr="ai_subtasks")
    )
    projects = Project.objects.filter(user=user).prefetch_related(
        Prefetch("task_set", queryset=task_queryset, to_attr="ai_tasks")
    ).order_by("pk")
    if project_id is not None:
        projects = projects.filter(pk=project_id)

    projects = projects[:25]
    return [
        {
            "id": project.pk,
            "name": project.name,
            "description": project.description[:500],
            "tasks": [
                {
                    "id": task.pk,
                    "title": task.title,
                    "description": task.description[:500],
                    "status": task.status,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "subtasks": [
                        {"title": subtask.title, "status": subtask.status}
                        for subtask in task.ai_subtasks
                    ],
                }
                for task in project.ai_tasks
            ],
        }
        for project in projects
    ]
