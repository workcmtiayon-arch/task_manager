# On importe le système de formulaires de Django
from django import forms

# On importe notre modèle Task
from .models import SubTask, Task


class TaskForm(forms.ModelForm):
    """
    Formulaire permettant de créer ou modifier une tâche.

    Le projet n'est volontairement PAS présent dans ce formulaire.
    Le projet est déterminé par la vue à partir du projet
    dans lequel l'utilisateur se trouve.
    """

    class Meta:
        # Le formulaire est basé sur le modèle Task
        model = Task

        # Champs que l'utilisateur peut créer ou modifier
        fields = [
            'title',
            'description',
            'status',
            'due_date'
        ]

        # Libellés affichés dans le formulaire
        labels = {
            'title': 'Task title',
            'description': 'Description',
            'status': 'Task status',
            'due_date': 'Task due date'
        }


class SubTaskForm(forms.ModelForm):
    class Meta:
        model = SubTask
        fields = ['title', 'position']
        labels = {
            'title': 'Subtask title',
            'position': 'Display position',
        }
        widgets = {
            'position': forms.NumberInput(attrs={'min': 0}),
        }
