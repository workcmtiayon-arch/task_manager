"""Build the smallest safe project context for an AI request."""

from projects.models import Project


def build_user_context(user, project_id=None):
    """Return only projects owned by ``user`` and their tasks/subtasks."""
    projects = Project.objects.filter(user=user).prefetch_related("task_set__subtasks")
    if project_id is not None:
        projects = projects.filter(pk=project_id)

    return [
        {
            "id": project.pk,
            "name": project.name,
            "description": project.description,
            "tasks": [
                {
                    "id": task.pk,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "subtasks": [
                        {"title": subtask.title, "status": subtask.status}
                        for subtask in task.subtasks.all()
                    ],
                }
                for task in project.task_set.all()
            ],
        }
        for project in projects
    ]
