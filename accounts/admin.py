from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'is_staff', 'date_joined']
    ordering = ['-date_joined']
    fieldsets = UserAdmin.fieldsets + ()

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'study_goal_hours', 'created_at']