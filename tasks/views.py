from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from projects.models import Project

from .forms import SubTaskForm, TaskForm
from .models import SubTask, Task


def _task_queryset(user):
    return Task.objects.filter(project__user=user).select_related('project').annotate(
        subtask_count=Count('subtasks', distinct=True),
        done_subtask_count=Count(
            'subtasks',
            filter=Q(subtasks__status=SubTask.Status.DONE),
            distinct=True,
        ),
    )


def _prepare_task(task):
    task.subtask_progress = (
        f'{task.done_subtask_count} / {task.subtask_count}'
        if task.subtask_count else None
    )
    return task


@login_required
def task_list(request):
    owned_tasks = Task.objects.filter(project__user=request.user)
    counts = owned_tasks.aggregate(
        total=Count('pk'),
        done=Count('pk', filter=Q(status=Task.Status.DONE)),
        in_progress=Count('pk', filter=Q(status=Task.Status.IN_PROGRESS)),
        todo=Count('pk', filter=Q(status=Task.Status.TODO)),
    )
    page_obj = Paginator(
        _task_queryset(request.user).order_by('due_date', '-created_at'), 50
    ).get_page(request.GET.get('page'))
    tasks = [_prepare_task(task) for task in page_obj.object_list]
    total_tasks = counts['total']
    done_tasks = counts['done']
    in_progress_tasks = counts['in_progress']
    todo_tasks = counts['todo']
    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'active_nav': 'tasks',
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'in_progress_tasks': in_progress_tasks,
        'todo_tasks': todo_tasks,
        'completion_percentage': round(done_tasks * 100 / total_tasks) if total_tasks else 0,
        'page_obj': page_obj,
    })


@login_required
@require_http_methods(["GET", "POST"])
def add_task(request, project_id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=project_id)
    form = TaskForm(request.POST or None)
    if form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.save()
        return redirect('project_detail', id=project.id)
    return render(request, 'tasks/task_form.html', {'form': form, 'active_nav': 'tasks'})


@login_required
@require_http_methods(["GET", "POST"])
def update_task(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    form = TaskForm(request.POST or None, instance=task)
    if form.is_valid():
        form.save()
        return redirect('project_detail', id=task.project.id)
    return render(request, 'tasks/task_form.html', {'form': form, 'task': task, 'active_nav': 'tasks'})


@login_required
@require_http_methods(["GET", "POST"])
def delete_task(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    project = task.project
    if request.method == 'POST':
        task.delete()
        return redirect('project_detail', id=project.id)
    return render(request, 'tasks/confirm_suppr_task.html', {'task': task, 'active_nav': 'tasks'})


@login_required
def task_detail(request, id):
    task = get_object_or_404(
        _task_queryset(request.user).prefetch_related('subtasks'),
        id=id,
    )
    task = _prepare_task(task)
    return render(request, 'tasks/task_detail.html', {'task': task, 'active_nav': 'tasks'})


@login_required
@require_POST
def task_update_status(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    if request.method == 'POST':
        if task.subtasks.exists():
            messages.info(request, _('This task status is managed automatically by its subtasks.'))
            return redirect('project_detail', id=task.project.id)
        status = request.POST.get('status')
        if status in Task.Status.values:
            task.status = status
            try:
                task.full_clean()
            except ValidationError:
                messages.error(request, _('The task cannot be completed until all its subtasks are completed.'))
            else:
                task.save(update_fields=['status', 'updated_at'])
    return redirect('project_detail', id=task.project.id)


@login_required
@require_http_methods(["GET", "POST"])
def add_subtask(request, task_id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=task_id)
    form = SubTaskForm(request.POST or None, initial={'position': task.subtasks.count()})
    if form.is_valid():
        subtask = form.save(commit=False)
        with transaction.atomic():
            # Lock the parent so concurrent additions through this endpoint
            # cannot select the same next position.
            task = Task.objects.select_for_update().get(pk=task.pk)
            subtask.task = task
            if 'position' not in request.POST:
                subtask.position = (task.subtasks.aggregate(max_position=Max('position'))['max_position'] or -1) + 1
            elif task.subtasks.filter(position=subtask.position).exists():
                form.add_error('position', _('This position is already used by another subtask.'))
            if not form.errors:
                subtask.save()
                return redirect('task_detail', id=task.id)
    return render(request, 'tasks/subtask_form.html', {'form': form, 'task': task, 'active_nav': 'tasks'})


@login_required
@require_POST
def toggle_subtask(request, id):
    subtask = get_object_or_404(SubTask.objects.filter(task__project__user=request.user), id=id)
    if request.method == 'POST':
        subtask.status = (
            SubTask.Status.NOT_DONE
            if subtask.status == SubTask.Status.DONE
            else SubTask.Status.DONE
        )
        subtask.save()
    return redirect('task_detail', id=subtask.task.id)


@login_required
@require_POST
def delete_subtask(request, id):
    subtask = get_object_or_404(SubTask.objects.filter(task__project__user=request.user), id=id)
    task_id = subtask.task.id
    if request.method == 'POST':
        subtask.delete()
    return redirect('task_detail', id=task_id)
