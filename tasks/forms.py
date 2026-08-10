# On importe le système de formulaires de Django
from django import forms

# On importe notre modèle Task
from .models import Task

# On importe le modèle Project de l'application projects
from projects.models import Project


# On crée un formulaire basé sur le modèle Task
class TaskForm(forms.ModelForm):

    # Le constructeur reçoit obligatoirement l'utilisateur connecté
    # depuis la vue : TaskForm(request.user, ...)
    def __init__(self, user, *args, **kwargs):

        # On initialise normalement le formulaire Django
        # avec les données éventuelles envoyées par l'utilisateur
        super().__init__(*args, **kwargs)

        # On récupère le champ "project" du formulaire
        # et on limite les projets proposés à ceux appartenant
        # uniquement à l'utilisateur actuellement connecté.
        self.fields['project'].queryset = Project.objects.filter(
            user=user
        )

    # La classe Meta indique à Django comment construire
    # automatiquement le formulaire à partir du modèle Task.
    class Meta:

        # Le formulaire est basé sur notre modèle Task
        model = Task

        # Voici les champs du modèle que l'utilisateur
        # pourra remplir dans le formulaire.
        fields = [
            'project',
            'title',
            'description',
            'status',
            'due_date'
        ]

        # On personnalise les labels affichés devant les champs.
        labels = {
            'project': 'Project of task',
            'title': 'Task title',
            'description': 'Description',
            'status': 'Task status',
            'due_date': 'Task due date'
        }