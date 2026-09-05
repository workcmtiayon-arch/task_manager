from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'user',
        'planned_start_date',
        'planned_end_date',
        'complexity',
        'temporal_status',
    )
    list_filter = ('complexity',)
    search_fields = ('name', 'description', 'user__username', 'user__email')
    readonly_fields = ('planned_end_date', 'temporal_status')
