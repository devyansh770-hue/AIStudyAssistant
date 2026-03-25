from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Course(models.Model):
    COMPLEXITY_CHOICES = [
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    exam_date = models.DateField()
    complexity = models.IntegerField(choices=COMPLEXITY_CHOICES, default=2)
    topics = models.TextField(help_text='Comma separated topics')
    daily_study_hours = models.PositiveIntegerField(default=2)
    hours_spent = models.FloatField(default=0.0)  # NEW
    ai_schedule = models.JSONField(blank=True, null=True, help_text='Stored AI generated schedule')
    exam_feedback = models.TextField(blank=True, help_text='User experience/feedback after exam')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['exam_date']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def days_until_exam(self):
        from django.utils import timezone
        today = timezone.now().date()
        delta = self.exam_date - today
        return delta.days

    def get_topics_list(self):
        return [t.strip() for t in self.topics.split(',') if t.strip()]

    def complexity_label(self):
        return dict(self.COMPLEXITY_CHOICES).get(self.complexity, 'Medium')

    def completion_percentage(self):
        from quizzes.models import QuizAttempt
        topics = self.get_topics_list()
        if not topics:
            return 0
        attempted_topics = QuizAttempt.objects.filter(
            course=self
        ).values_list('topic', flat=True).distinct()
        done = sum(1 for t in topics if t in attempted_topics)
        return round((done / len(topics)) * 100)

    def total_study_hours_goal(self):
        days = self.days_until_exam()
        return max(days, 0) * self.daily_study_hours


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topic_set')
    name = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.course.name}"