from django.contrib import admin
from .models import Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'salary', 'is_active', 'is_approved', 'created_at')
    list_filter = ('is_active', 'is_approved', 'job_type', 'salary', 'created_at')
    search_fields = ('title', 'company', 'description', 'location')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_editable = ('is_active', 'is_approved')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('job__title', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('applied_at', 'updated_at')
    date_hierarchy = 'applied_at'
    list_editable = ('status',)
