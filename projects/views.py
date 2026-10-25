from collections import Counter, deque

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
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


def _project_page_context(project_queryset, view_mode, request):
    try:
        requested_page = max(1, int(request.GET.get('page', '1')))
    except (TypeError, ValueError):
        requested_page = 1

    page_size = 24
    page_start = (requested_page - 1) * page_size
    selected_count = 0
    total_task_count = 0
    completed_task_count = 0
    status_counts = Counter()
    requested_projects = []
    last_projects = deque(maxlen=page_size)

    for project in project_queryset.iterator(chunk_size=200):
        _prepare_project(project)
        status_counts[project.display_status] += 1
        if view_mode == 'active':
            is_displayed = project.display_status in ACTIVE_STATUSES
        elif view_mode == 'completed':
            is_displayed = project.display_status == Project.TemporalStatus.COMPLETED
        else:
            is_displayed = project.display_status == Project.TemporalStatus.UPCOMING
        if not is_displayed:
            continue

        total_task_count += project.task_count
        completed_task_count += project.done_count
        if page_start <= selected_count < page_start + page_size:
            requested_projects.append(project)
        last_projects.append(project)
        selected_count += 1

    paginator = Paginator(range(selected_count), page_size)
    page_obj = paginator.get_page(requested_page)
    if page_obj.number != requested_page:
        requested_projects = list(last_projects)
    page_obj.object_list = requested_projects

    return {
        'projects': page_obj,
        'page_obj': page_obj,
        'active_nav': 'projects',
        'view_mode': view_mode,
        'project_count': selected_count,
        'total_task_count': total_task_count,
        'completed_task_count': completed_task_count,
        'completed_project_count': status_counts[Project.TemporalStatus.COMPLETED],
        'project_completion_percentage': (
            round(completed_task_count * 100 / total_task_count)
            if total_task_count else 0
        ),
        'status_counts': {
            status: status_counts[status]
            for status in Project.TemporalStatus.values
        },
    }


@login_required
def project_list(request):
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(_project_queryset(request.user), 'active', request),
    )


@login_required
def completed_project_list(request):
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(_project_queryset(request.user), 'completed', request),
    )


@login_required
def upcoming_project_list(request):
    return render(
        request,
        'projects/project_list.html',
        _project_page_context(_project_queryset(request.user), 'upcoming', request),
    )


@login_required
@require_http_methods(["GET", "POST"])
def add_project(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save(commit=False)
        project.user = request.user
        project.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form': form, 'active_nav': 'projects'})


@login_required
@require_http_methods(["GET", "POST"])
def update_project(request, id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    form = ProjectForm(request.POST or None, instance=project)
    if form.is_valid():
        form.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form': form, 'project': project, 'active_nav': 'projects'})


@login_required
@require_http_methods(["GET", "POST"])
def delete_project(request, id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    if request.method == 'POST':
        project.delete()
        return redirect('project_list')
    return render(request, 'projects/confirm_supp_project.html', {'project': project, 'active_nav': 'projects'})


@login_required
def project_detail(request, id):
    project = _prepare_project(get_object_or_404(_project_queryset(request.user), id=id))
    tasks = list(
        project.task_set.all()
        .prefetch_related('subtasks')
        .order_by('due_date', '-created_at')
    )
    today = timezone.localdate()
    for task in tasks:
        task.is_overdue = bool(task.due_date and task.due_date < today and task.status != 'DONE')
        task.subtask_count = len(task.subtasks.all())
        task.done_subtask_count = sum(
            subtask.status == 'DONE' for subtask in task.subtasks.all()
        )
    project.project_tasks = tasks
    project.in_progress_count = sum(task.status == 'IN_PROGRESS' for task in tasks)
    project.todo_count = sum(task.status == 'TODO' for task in tasks)
    project.done_percent = project.progress_percent
    project.in_progress_percent = round(project.in_progress_count * 100 / project.task_count) if project.task_count else 0
    project.todo_percent = round(project.todo_count * 100 / project.task_count) if project.task_count else 0
    return render(request, 'projects/project_detail.html', {'project': project, 'active_nav': 'projects'})
