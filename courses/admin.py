from django.contrib import admin
from .models import Course, Topic

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'exam_date', 'complexity', 'created_at']
    list_filter = ['complexity']
    search_fields = ['name', 'user__email']

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'is_completed']