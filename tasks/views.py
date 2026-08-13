# On importe les fonctions nécessaires de Django
from django.shortcuts import render, redirect, get_object_or_404

# On importe le modèle Task
from .models import Task

# On importe le formulaire TaskForm
from .forms import TaskForm

# On importe le modèle Project
from projects.models import Project


def task_list(request):
    """
    Affiche toutes les tâches appartenant aux projets
    de l'utilisateur actuellement connecté.
    """

    # On récupère uniquement les tâches dont le projet
    # appartient à l'utilisateur connecté.
    tasks = Task.objects.filter(
        project__user=request.user
    )

    # On envoie les tâches au template.
    return render(
        request,
        'tasks/task_list.html',
        {'tasks': tasks}
    )

def add_task(request, project_id):
    """
    Crée une nouvelle tâche dans le projet depuis lequel
    l'utilisateur a lancé la création.
    """

    # On récupère le projet demandé uniquement s'il appartient
    # à l'utilisateur connecté.
    project = get_object_or_404(
        Project.objects.filter(user=request.user),
        id=project_id
    )

    # On crée le formulaire avec les données POST si elles existent.
    form = TaskForm(
        request.POST or None
    )

    # On vérifie que les données du formulaire sont valides.
    if form.is_valid():

        # On crée l'objet Task en mémoire sans encore
        # l'enregistrer dans la base de données.
        task = form.save(commit=False)

        # On rattache automatiquement la tâche
        # au projet depuis lequel elle a été créée.
        task.project = project

        # On enregistre maintenant la tâche en base de données.
        task.save()

        # Après la création, on retourne exactement
        # au projet depuis lequel la création a été lancée.
        return redirect(
            'project_detail',
            id=project.id
        )

    # Si le formulaire n'est pas valide,
    # on réaffiche le formulaire avec ses erreurs.
    return render(
        request,
        'tasks/task_form.html',
        {'form': form}
    )

def update_task(request, id):
    """
    Modifie une tâche appartenant à l'utilisateur connecté.

    Le projet de la tâche ne peut pas être modifié.
    """

    # On récupère uniquement une tâche appartenant
    # à un projet de l'utilisateur connecté.
    task = get_object_or_404(
        Task.objects.filter(
            project__user=request.user
        ),
        id=id
    )

    # On récupère le projet auquel la tâche appartient.
    project = task.project

    # On initialise le formulaire avec les données existantes
    # de la tâche.
    form = TaskForm(
        request.POST or None,
        instance=task
    )

    # On vérifie les données envoyées.
    if form.is_valid():

        # On sauvegarde les modifications.
        form.save()

        # Après la modification, on retourne exactement
        # au projet dans lequel se trouvait la tâche.
        return redirect(
            'project_details',
            id=project.id
        )

    # Si le formulaire est invalide, on réaffiche
    # le formulaire avec les erreurs.
    return render(
        request,
        'tasks/task_form.html',
        {'form': form}
    )


def delete_task(request, id):
    """
    Supprime une tâche appartenant à l'utilisateur connecté.
    """

    # On récupère uniquement une tâche appartenant
    # à un projet de l'utilisateur connecté.
    task = get_object_or_404(
        Task.objects.filter(
            project__user=request.user
        ),
        id=id
    )

    # On mémorise le projet avant de supprimer la tâche.
    project = task.project

    # La suppression est effectuée uniquement avec une requête POST.
    if request.method == 'POST':

        # Suppression de la tâche.
        task.delete()

        # Après suppression, retour au projet concerné.
        return redirect(
            'project_detail',
            id=project.id
        )

    # Si la requête est GET, on affiche la page
    # de confirmation de suppression.
    return render(
        request,
        'tasks/confirm_suppr_task.html',
        {'task': task}
    )


def task_detail(request, id):
    """
    Affiche les détails d'une tâche appartenant
    à l'utilisateur connecté.
    """

    # On empêche l'utilisateur d'accéder à une tâche
    # appartenant à un autre utilisateur.
    task = get_object_or_404(
        Task.objects.filter(
            project__user=request.user
        ),
        id=id
    )

    # On affiche les détails de la tâche.
    return render(
        request,
        'tasks/task_detail.html',
        {'task': task}
    )


def task_update_status(request, id):
    # On récupère uniquement une tâche appartenant à un projet
    # de l'utilisateur actuellement connecté.
    task = get_object_or_404(
        Task.objects.filter(project__user=request.user),
        id=id
    )

    # La modification du statut doit obligatoirement être faite en POST.
    if request.method == 'POST':

        # On récupère le nouveau statut envoyé par le formulaire.
        status = request.POST.get('status')

        # On vérifie que le statut envoyé fait partie des statuts autorisés.
        if status in ['TODO', 'IN_PROGRESS', 'DONE']:

            # On modifie uniquement le statut de la tâche.
            task.status = status

            # On sauvegarde la modification en base de données.
            task.save(update_fields=['status'])

    # Après la modification, on retourne sur la page du projet
    # dans lequel se trouvait la tâche.
    return redirect('project_detail', id=task.project.id)