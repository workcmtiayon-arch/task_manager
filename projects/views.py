from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q

from .models import Project
from .forms import ProjectForm


# Première fonction pour l'affichage des projets
def project_list(request):
    # On récupère uniquement les projets appartenant à l'utilisateur connecté.
    # On calcule également le nombre total de tâches et le nombre de tâches terminées.
    projects = Project.objects.filter(
        user=request.user
    ).annotate(
        task_count=Count('task'),
        done_count=Count(
            'task',
            filter=Q(task__status='DONE')
        ),
    )

    # Pour chaque projet, on calcule le pourcentage de tâches terminées.
    for project in projects:
        project.progress_percent = (
            round((project.done_count / project.task_count) * 100)
            if project.task_count
            else 0
        )

    return render(
        request,
        'projects/project_list.html',
        {'projects': projects}
    )


# Deuxième fonction permettant d'ajouter un nouveau projet
def add_project(request):
    form = ProjectForm(request.POST or None)

    if form.is_valid():
        # On crée l'objet en mémoire sans encore l'enregistrer.
        project = form.save(commit=False)

        # L'utilisateur connecté devient automatiquement propriétaire.
        project.user = request.user

        # On enregistre le projet dans la base de données.
        project.save()

        return redirect('project_list')

    return render(
        request,
        'projects/project_form.html',
        {'form': form}
    )


# Troisième fonction permettant de modifier un projet
def update_project(request, id):
    # On autorise uniquement la modification d'un projet appartenant
    # à l'utilisateur actuellement connecté.
    project = get_object_or_404(
        Project.objects.filter(user=request.user),
        id=id
    )

    # On initialise le formulaire avec les données existantes du projet.
    form = ProjectForm(
        request.POST or None,
        instance=project
    )

    if form.is_valid():
        # On sauvegarde les modifications.
        project = form.save(commit=False)
        project.save()

        return redirect('project_list')

    return render(
        request,
        'projects/project_form.html',
        {'form': form}
    )


# Quatrième fonction permettant de supprimer un projet
def delete_project(request, id):
    # On récupère uniquement un projet appartenant à l'utilisateur connecté.
    project = get_object_or_404(
        Project.objects.filter(user=request.user),
        id=id
    )

    if request.method == 'POST':
        # Suppression du projet.
        project.delete()

        return redirect('project_list')

    return render(
        request,
        'projects/confirm_supp_project.html',
        {'project': project}
    )


# Fonction permettant d'afficher le détail d'un projet
def project_detail(request, id):
    project = get_object_or_404(
        Project.objects.filter(user=request.user).annotate(
            task_count=Count('task'),
            done_count=Count(
                'task',
                filter=Q(task__status='DONE')
            ),
            in_progress_count=Count(
                'task',
                filter=Q(task__status='IN_PROGRESS')
            ),
            todo_count=Count(
                'task',
                filter=Q(task__status='TODO')
            ),
        ),
        id=id
    )

    # Pourcentage global de progression
    project.progress_percent = (
        round((project.done_count / project.task_count) * 100)
        if project.task_count else 0
    )

    # Pourcentage de tâches terminées
    project.done_percent = (
        round((project.done_count / project.task_count) * 100)
        if project.task_count else 0
    )

    # Pourcentage de tâches en cours
    project.in_progress_percent = (
        round((project.in_progress_count / project.task_count) * 100)
        if project.task_count else 0
    )

    # Pourcentage de tâches à faire
    project.todo_percent = (
        round((project.todo_count / project.task_count) * 100)
        if project.task_count else 0
    )

    return render(
        request,
        'projects/project_detail.html',
        {'project': project}
    )