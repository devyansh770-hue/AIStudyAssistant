from django.contrib import admin
from .models import Question, QuizAttempt

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['topic', 'course', 'difficulty', 'created_at']

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'topic', 'score_percent', 'created_at']