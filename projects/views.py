from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ProjectForm
from .models import Project

ACTIVE_STATUSES = (
    Project.TemporalStatus.IN_PROGRESS,
    Project.TemporalStatus.OVERDUE,
)


def _project_queryset(user):
    today = timezone.localdate()
    return Project.objects.filter(user=user).annotate(
        task_count=Count('task', distinct=True),
        done_count=Count('task', filter=Q(task__status='DONE'), distinct=True),
        late_task_count=Count(
            'task',
            filter=Q(task__due_date__lt=today) & ~Q(task__status='DONE'),
            distinct=True,
        ),
    )


def _status_for_counts(project):
    if project.task_count and project.done_count == project.task_count:
        return Project.TemporalStatus.COMPLETED
    today = timezone.localdate()
    if today < project.planned_start_date:
        return Project.TemporalStatus.UPCOMING
    if today > project.planned_end_date:
        return Project.TemporalStatus.OVERDUE
    return Project.TemporalStatus.IN_PROGRESS


def _prepare_project(project):
    project.progress_percent = round(project.done_count * 100 / project.task_count) if project.task_count else 0
    project.display_status = _status_for_counts(project)
    return project


def _project_page_context(all_projects, displayed_projects, view_mode):
    total_task_count = sum(project.task_count for project in displayed_projects)
    completed_task_count = sum(project.done_count for project in displayed_projects)
    return {
        'projects': displayed_projects,
        'active_nav': 'projects',
        'view_mode': view_mode,
        'project_count': len(displayed_projects),
        'total_task_count': total_task_count,
        'completed_task_count': completed_task_count,
        'completed_project_count': sum(
            project.display_status == Project.TemporalStatus.COMPLETED
            for project in all_projects
        ),
        'project_completion_percentage': (
            round(completed_task_count * 100 / total_task_count)
            if total_task_count else 0
        ),
        'status_counts': {
            status: sum(project.display_status == status for project in all_projects)
            for status in Project.TemporalStatus.values
        },
    }


@login_required
def project_list(request):
    all_projects = [_prepare_project(project) for project in _project_queryset(request.user)]
    displayed_projects = [
        project for project in all_projects if project.display_status in ACTIVE_STATUSES
    ]
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(all_projects, displayed_projects, 'active'),
    )


@login_required
def completed_project_list(request):
    all_projects = [_prepare_project(project) for project in _project_queryset(request.user)]
    displayed_projects = [
        project for project in all_projects
        if project.display_status == Project.TemporalStatus.COMPLETED
    ]
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(all_projects, displayed_projects, 'completed'),
    )


@login_required
def upcoming_project_list(request):
    all_projects = [_prepare_project(project) for project in _project_queryset(request.user)]
    displayed_projects = [
        project for project in all_projects
        if project.display_status == Project.TemporalStatus.UPCOMING
    ]
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(all_projects, displayed_projects, 'upcoming'),
    )


@login_required
def add_project(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save(commit=False)
        project.user = request.user
        project.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form': form, 'active_nav': 'projects'})


@login_required
def update_project(request, id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    form = ProjectForm(request.POST or None, instance=project)
    if form.is_valid():
        form.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form': form, 'project': project, 'active_nav': 'projects'})


@login_required
def delete_project(request, id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    if request.method == 'POST':
        project.delete()
        return redirect('project_list')
    return render(request, 'projects/confirm_supp_project.html', {'project': project, 'active_nav': 'projects'})


@login_required
def project_detail(request, id):
    project = _prepare_project(get_object_or_404(_project_queryset(request.user), id=id))
    tasks = list(project.task_set.all().order_by('due_date', '-created_at'))
    today = timezone.localdate()
    for task in tasks:
        task.is_overdue = bool(task.due_date and task.due_date < today and task.status != 'DONE')
    project.project_tasks = tasks
    project.in_progress_count = sum(task.status == 'IN_PROGRESS' for task in tasks)
    project.todo_count = sum(task.status == 'TODO' for task in tasks)
    project.done_percent = project.progress_percent
    project.in_progress_percent = round(project.in_progress_count * 100 / project.task_count) if project.task_count else 0
    project.todo_percent = round(project.todo_count * 100 / project.task_count) if project.task_count else 0
    return render(request, 'projects/project_detail.html', {'project': project, 'active_nav': 'projects'})
