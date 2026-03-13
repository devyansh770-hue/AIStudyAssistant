from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()

class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions')
    topic = models.CharField(max_length=200)
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_answer = models.CharField(max_length=300)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic}: {self.question_text[:60]}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attempts')
    topic = models.CharField(max_length=200)
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    score_percent = models.FloatField(default=0.0)
    time_taken_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.course.name} - {self.score_percent}%"