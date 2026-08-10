from django.shortcuts import render, redirect, get_object_or_404
from .models import Project
from .forms import ProjectForm

# Create your views here.
# Premiere fonction pour l'affichage des projets
def projects_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'projects/project_list.html', {'projects' : projects})

# Deuxieme fonction permettant d'ajouter un nouveau projet
def add_project(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        # je cree un objet en memoire sans le faire enregistrer avec mon commit=False
        project = form.save(commit=False)
        # Faire en sorte que l'utilisateur connecte soit le proprietaire du projet
        project.user = request.user
        # Enregistrer dans la base de donnees
        project.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form' : form})

# Troisieme fonction permettant la modification des informations d'un employe
def update_project(request, id):
    # Recuete le projet grace a son ID ou affiche 404 error
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    # Initialise le formulaire avec les donnees envoyees (post) et l'instance du projet a modifier
    form = ProjectForm(request.POST or None, instance=project)
    # Verifie la validite des donnees entree dans le formulaire
    if form.is_valid():
        # Cree l'objet mis a jour dans la memoire sans l'enregistrer dans la BD
        project = form.save(commit=False)
        project.save()
        return redirect('project_list')
    return render(request, 'projects/project_form.html', {'form' : form})

#Quatrieme fonction permettant la suppression d'un employe
def delete_project(request, id) :
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    if request.method == "POST" :
        project.delete()
        return redirect('project_list')
    return render(request, 'projects/confirm_supp_project.html', {'project' : project})

def project_detail(request, id):
    project = get_object_or_404(Project.objects.filter(user=request.user), id=id)
    return render(request, 'projects/project_detail.html', {'project' : project})