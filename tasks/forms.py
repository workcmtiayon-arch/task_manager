# On importe le système de formulaires de Django
from django import forms
from django.utils.translation import gettext_lazy as _

# On importe notre modèle Task
from .models import SubTask, Task


class TaskForm(forms.ModelForm):
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.subtasks.exists():
            self.fields['status'].disabled = True
            self.fields['status'].help_text = _('The status is managed automatically by subtasks.')
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
            'title': _('Task title'),
            'description': _('Description'),
            'status': _('Task status'),
            'due_date': _('Due date'),
        }
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class SubTaskForm(forms.ModelForm):
    position = forms.IntegerField(min_value=0, required=False, label=_('Display position'))

    class Meta:
        model = SubTask
        fields = ['title', 'position']
        labels = {
            'title': _('Subtask title'),
            'position': _('Display position'),
        }
        widgets = {
            'position': forms.NumberInput(attrs={'min': 0, 'class': 'form-input'}),
        }
