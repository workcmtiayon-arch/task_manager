# On importe le système de formulaires de Django
from django import forms

# On importe notre modèle Task
from .models import SubTask, Task


class TaskForm(forms.ModelForm):
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.subtasks.exists():
            self.fields['status'].disabled = True
            self.fields['status'].help_text = 'Le statut est géré automatiquement par les SubTasks.'
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
            'title': 'Titre de la tâche',
            'description': 'Description',
            'status': 'Statut de la tâche',
            'due_date': "Date d'échéance",
        }
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class SubTaskForm(forms.ModelForm):
    position = forms.IntegerField(min_value=0, required=False, label='Position d’affichage')

    class Meta:
        model = SubTask
        fields = ['title', 'position']
        labels = {
            'title': 'Titre de la SubTask',
            'position': 'Position d’affichage',
        }
        widgets = {
            'position': forms.NumberInput(attrs={'min': 0}),
        }
