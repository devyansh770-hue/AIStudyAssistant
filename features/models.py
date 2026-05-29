from django.db import models
from django.conf import settings

# A basic Concept model to track topics/concepts for Feature #3 and #4
class Concept(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserEngagementMetrics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey('quizzes.QuizAttempt', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Raw data
    response_time_ms = models.IntegerField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    total_questions_in_session = models.IntegerField(default=0)
    correct_answers_in_session = models.IntegerField(default=0)
    session_duration_minutes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Calculated metrics (Feature #1)
    response_quality = models.FloatField(null=True, blank=True)
    interaction_frequency = models.FloatField(null=True, blank=True)
    time_pressure = models.FloatField(null=True, blank=True)
    engagement_score = models.FloatField(null=True, blank=True)
    fatigue_factor = models.FloatField(null=True, blank=True)
    error_decay = models.FloatField(null=True, blank=True)
    load_variable_L = models.FloatField(null=True, blank=True)
    
    # Flow Zone Status
    is_in_flow_zone = models.BooleanField(default=False)
    flow_zone_entry_time = models.DateTimeField(null=True, blank=True)
    time_in_flow_zone_minutes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Session Actions
    difficulty_adjustment = models.CharField(max_length=50, null=True, blank=True)
    break_recommended = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'session']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Engagement: {self.engagement_score}"


class ErrorAnalysisLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey('quizzes.QuizAttempt', on_delete=models.CASCADE)
    question = models.ForeignKey('quizzes.Question', on_delete=models.CASCADE)
    
    # Error Details
    error_type = models.CharField(max_length=100, blank=True, null=True)
    user_response = models.TextField(blank=True, null=True)
    correct_response = models.TextField(blank=True, null=True)
    
    # Student Context
    response_time_ms = models.IntegerField(null=True, blank=True)
    accuracy_on_topic_percent = models.IntegerField(default=0)
    session_duration_minutes = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    consecutive_errors = models.IntegerField(default=0)
    
    # STAGE 1: Heuristic Classification
    heuristic_rule_matched = models.CharField(max_length=100, blank=True, null=True)
    heuristic_confidence = models.FloatField(null=True, blank=True)
    heuristic_category = models.CharField(max_length=100, blank=True, null=True)
    
    # STAGE 2: LLM Classification
    was_sent_to_llm = models.BooleanField(default=False)
    llm_response_time_ms = models.IntegerField(null=True, blank=True)
    llm_category = models.CharField(max_length=100, blank=True, null=True)
    gemini_explanation = models.TextField(blank=True, null=True)
    
    # Cost & Performance Tracking
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    api_cost_usd = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    total_latency_ms = models.IntegerField(null=True, blank=True)
    explanation_quality_rating = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'session']),
            models.Index(fields=['created_at']),
        ]


class KnowledgeGraphMetrics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    
    # Concept Information
    concept_importance = models.FloatField(default=0.5)
    
    # Mastery State
    questions_attempted = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    mastery_percent = models.IntegerField(default=0)
    node_color = models.CharField(max_length=20, default='RED')
    
    # Prerequisites
    prerequisite_count = models.IntegerField(default=0)
    prerequisite_strength_avg = models.FloatField(default=0.0)
    all_prerequisites_mastered = models.BooleanField(default=False)
    
    # Timing
    first_introduced_date = models.DateField(auto_now_add=True)
    last_mastery_update = models.DateTimeField(auto_now=True)
    recommended_next_concept = models.ForeignKey(Concept, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    recommendation_accepted = models.BooleanField(default=False)
    
    # Performance
    recommendation_latency_ms = models.IntegerField(null=True, blank=True)
    graph_construction_time_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'concept']),
            models.Index(fields=['user', 'mastery_percent']),
        ]


class SpacedRepetitionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE)
    
    # Review Interval Calculation
    base_interval_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_days_remaining = models.IntegerField(null=True, blank=True)
    
    # Weight Factors (Feature #4)
    weight_exam = models.FloatField(default=1.0)
    weight_difficulty = models.FloatField(default=1.0)
    weight_peer = models.FloatField(default=1.0)
    
    # Final Schedule
    final_interval_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    scheduled_review_date = models.DateField(null=True, blank=True)
    
    # Review Status
    review_completed = models.BooleanField(default=False)
    completion_date = models.DateField(null=True, blank=True)
    performance_on_review = models.IntegerField(default=0)
    
    # Metrics
    time_since_last_review_days = models.IntegerField(default=0)
    time_to_mastery_days = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'scheduled_review_date']),
        ]


class DailyMetricsAggregate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_recorded = models.DateField(auto_now_add=True)
    
    # Feature #1 Aggregates
    avg_engagement_score = models.FloatField(null=True, blank=True)
    percent_time_in_flow_zone = models.FloatField(null=True, blank=True)
    num_sessions_today = models.IntegerField(default=0)
    num_breaks_recommended = models.IntegerField(default=0)
    
    # Feature #2 Aggregates
    total_errors = models.IntegerField(default=0)
    heuristic_resolved = models.IntegerField(default=0)
    llm_resolved = models.IntegerField(default=0)
    total_api_cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0.0)
    avg_explanation_quality = models.FloatField(null=True, blank=True)
    
    # Feature #3 Aggregates
    concepts_mastered = models.IntegerField(default=0)
    concepts_learning = models.IntegerField(default=0)
    concepts_not_started = models.IntegerField(default=0)
    avg_prerequisite_strength = models.FloatField(null=True, blank=True)
    
    # Feature #4 Aggregates
    topics_scheduled_today = models.IntegerField(default=0)
    topics_completed_today = models.IntegerField(default=0)
    estimated_days_to_full_mastery = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date_recorded']),
        ]
