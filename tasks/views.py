from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

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
    tasks = [_prepare_task(task) for task in _task_queryset(request.user).order_by('due_date', '-created_at')]
    total_tasks = len(tasks)
    done_tasks = sum(task.status == Task.Status.DONE for task in tasks)
    in_progress_tasks = sum(task.status == Task.Status.IN_PROGRESS for task in tasks)
    todo_tasks = sum(task.status == Task.Status.TODO for task in tasks)
    return render(request, 'tasks/task_list.html', {
        'tasks': tasks,
        'active_nav': 'tasks',
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'in_progress_tasks': in_progress_tasks,
        'todo_tasks': todo_tasks,
        'completion_percentage': round(done_tasks * 100 / total_tasks) if total_tasks else 0,
    })


@login_required
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
def update_task(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    form = TaskForm(request.POST or None, instance=task)
    if form.is_valid():
        form.save()
        return redirect('project_detail', id=task.project.id)
    return render(request, 'tasks/task_form.html', {'form': form, 'task': task, 'active_nav': 'tasks'})


@login_required
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
def task_update_status(request, id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in Task.Status.values:
            task.status = status
            try:
                task.full_clean()
            except ValidationError:
                messages.error(request, 'La tâche ne peut pas être terminée tant que toutes ses SubTasks ne le sont pas.')
            else:
                task.save(update_fields=['status', 'updated_at'])
    return redirect('project_detail', id=task.project.id)


@login_required
def add_subtask(request, task_id):
    task = get_object_or_404(Task.objects.filter(project__user=request.user), id=task_id)
    form = SubTaskForm(request.POST or None, initial={'position': task.subtasks.count()})
    if form.is_valid():
        subtask = form.save(commit=False)
        subtask.task = task
        if 'position' not in form.changed_data:
            subtask.position = task.subtasks.count()
        subtask.save()
        return redirect('task_detail', id=task.id)
    return render(request, 'tasks/subtask_form.html', {'form': form, 'task': task, 'active_nav': 'tasks'})


@login_required
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
def delete_subtask(request, id):
    subtask = get_object_or_404(SubTask.objects.filter(task__project__user=request.user), id=id)
    task_id = subtask.task.id
    if request.method == 'POST':
        subtask.delete()
    return redirect('task_detail', id=task_id)
