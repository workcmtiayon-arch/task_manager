from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name',
            'description',
            'planned_start_date',
            'planned_duration_days',
            'complexity',
        ]
        labels = {
            'name': _('Project name'),
            'description': _('Description'),
            'planned_start_date': _('Planned start date'),
            'planned_duration_days': _('Planned duration (days)'),
            'complexity': _('Complexity'),
        }
        widgets = {
            'planned_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'planned_duration_days': forms.NumberInput(attrs={'min': 1, 'class': 'form-input'}),
            'complexity': forms.Select(attrs={'class': 'form-select'}),
        }
