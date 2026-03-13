from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('questions/<int:course_id>/', views.generate_questions_view, name='generate_questions'),
    path('api/questions/', views.api_generate_questions, name='api_questions'),
    path('schedule/<int:course_id>/', views.view_schedule, name='schedule'),
    path('chat/<int:course_id>/', views.tutor_chat_view, name='chat'),
    path('api/chat/', views.api_tutor_chat, name='api_chat'),
]