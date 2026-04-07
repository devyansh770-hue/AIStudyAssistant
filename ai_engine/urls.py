from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    # ── Existing ──
    path('questions/<int:course_id>/',        views.generate_questions_view,  name='generate_questions'),
    path('api/questions/',                     views.api_generate_questions,   name='api_questions'),
    path('schedule/<int:course_id>/',          views.view_schedule,            name='schedule'),
    path('api/schedule/toggle-task/',          views.toggle_task_completion,   name='api_toggle_task'),
    path('api/schedule/delete/<int:history_id>/', views.delete_schedule,        name='delete_schedule'),
    path('global-schedule/',                   views.global_schedule_view,     name='global_schedule'),
    path('chat/<int:course_id>/',              views.tutor_chat_view,          name='chat'),
    path('api/chat/',                          views.api_tutor_chat,           name='api_chat'),

    # ── Feature 1: Predictive Exam Score Estimator ──
    path('predict/<int:course_id>/',           views.predict_score_view,       name='predict_score'),
    path('api/predict/',                       views.api_predict_score,        name='api_predict_score'),

    # ── Feature 2: Mistake Pattern Analyzer ──
    path('mistakes/<int:course_id>/',          views.mistake_analysis_view,    name='mistake_analysis'),

    # ── Feature 3: Spaced Repetition Queue ──
    path('review-queue/',                      views.review_queue_view,        name='review_queue'),
    path('api/review-complete/',               views.api_review_complete,      name='api_review_complete'),

    # ── Feature 4: Cognitive Load ──
    path('api/cognitive/update/',              views.api_cognitive_update,     name='api_cognitive_update'),
    path('api/cognitive/summarize/',           views.api_cognitive_summarize,  name='api_cognitive_summarize'),

    # ── Feature 5: Knowledge Graph ──
    path('knowledge-graph/<int:course_id>/',   views.knowledge_graph_view,     name='knowledge_graph'),
    path('api/build-graph/',                   views.api_build_graph,          name='api_build_graph'),

    # ── Feature 6: Cross-Course Concept Linker ──
    path('concept-links/',                     views.concept_links_view,       name='concept_links'),
    path('api/find-links/',                    views.api_find_links,           name='api_find_links'),
]