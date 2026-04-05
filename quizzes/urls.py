from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    path('setup/<int:course_id>/', views.quiz_setup, name='setup'),
    path('attempt/<int:course_id>/', views.quiz_attempt, name='attempt'),
    path('submit/', views.quiz_submit, name='submit'),
    path('history/<int:course_id>/', views.quiz_history, name='history'),
    path('dismiss-surprise/', views.dismiss_surprise, name='dismiss_surprise'),
]