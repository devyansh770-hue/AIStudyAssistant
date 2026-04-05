from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MistakePattern(models.Model):
    """Caches Gemini-analyzed mistake patterns per user per course."""
    PATTERN_TYPES = [
        ('topic_weakness',       'Topic Weakness'),
        ('difficulty_ceiling',   'Difficulty Ceiling'),
        ('time_pressure',        'Time Pressure'),
        ('conceptual_confusion', 'Conceptual Confusion'),
    ]
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mistake_patterns')
    course       = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='mistake_patterns')
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPES)
    details      = models.JSONField(default=dict)      # structured insight data
    gemini_insight = models.TextField(blank=True)       # NLP-generated explanation
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} — {self.course.name} — {self.pattern_type}"


class SpacedRepetitionCard(models.Model):
    """SM-2 spaced-repetition state per user/course/topic."""
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sr_cards')
    course           = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='sr_cards')
    topic            = models.CharField(max_length=200)
    easiness_factor  = models.FloatField(default=2.5)   # SM-2 E-Factor (>=1.3)
    interval_days    = models.IntegerField(default=1)    # days until next review
    repetition_count = models.IntegerField(default=0)   # total times reviewed
    next_review_date = models.DateField()
    last_review_date = models.DateField(null=True, blank=True)
    last_quality     = models.IntegerField(default=0)   # 0-5 SM-2 quality score

    class Meta:
        unique_together = ['user', 'course', 'topic']
        ordering = ['next_review_date']

    def __str__(self):
        return f"SR: {self.user.username} — {self.topic} (next: {self.next_review_date})"

    def is_due(self):
        from django.utils import timezone
        return self.next_review_date <= timezone.now().date()


class CognitiveLoadSession(models.Model):
    """Records cognitive-load metrics for a quiz session."""
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cognitive_sessions')
    course             = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='cognitive_sessions')
    topic              = models.CharField(max_length=200, blank=True)
    session_data       = models.JSONField(default=list)   # per-question load snapshots
    avg_cognitive_load = models.FloatField(default=0.5)   # 0.0–1.0
    flow_zone_percent  = models.FloatField(default=0.0)   # % of questions in "flow" zone
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"CogLoad: {self.user.username} — {self.course.name} ({self.avg_cognitive_load:.2f})"


class KnowledgeGraph(models.Model):
    """Stores the Gemini-built concept graph for a course."""
    course       = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='knowledge_graph')
    graph_data   = models.JSONField(default=dict)   # { nodes: [...], edges: [...] }
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KG: {self.course.name}"


class ConceptLink(models.Model):
    """Shared concepts between two courses for the same user."""
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='concept_links')
    source_course   = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='concept_links_from')
    target_course   = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='concept_links_to')
    shared_concepts = models.JSONField(default=list)  # [{concept, similarity_score, source_topic, target_topic}]
    last_updated    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'source_course', 'target_course']

    def __str__(self):
        return f"Link: {self.source_course.name} ↔ {self.target_course.name}"
