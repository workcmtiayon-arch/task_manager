from django import forms

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
            'name': 'Project name',
            'description': 'Description',
            'planned_start_date': 'Planned start date',
            'planned_duration_days': 'Planned duration (days)',
            'complexity': 'Complexity',
        }
        widgets = {
            'planned_start_date': forms.DateInput(attrs={'type': 'date'}),
            'planned_duration_days': forms.NumberInput(attrs={'min': 1}),
        }
