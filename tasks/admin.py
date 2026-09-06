from django.contrib import admin
from .models import SubTask, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'subtask_summary', 'due_date')
    list_filter = ('status',)
    search_fields = ('title', 'description', 'project__name')

    @admin.display(description='SubTasks')
    def subtask_summary(self, task):
        total = task.subtasks.count()
        done = task.subtasks.filter(status=SubTask.Status.DONE).count()
        return f'{done} / {total}' if total else '—'


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'task', 'status', 'position', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title', 'task__title', 'task__project__name')
