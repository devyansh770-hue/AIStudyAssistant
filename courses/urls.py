from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('create/', views.course_create, name='create'),
    path('<int:pk>/', views.course_detail, name='detail'),
    path('<int:pk>/edit/', views.course_edit, name='edit'),
    path('<int:pk>/delete/', views.course_delete, name='delete'),
    path('<int:pk>/log-hours/', views.log_hours, name='log_hours'),
    path('<int:pk>/log-experience/', views.log_experience, name='log_experience'),
    path('topic/<int:pk>/toggle/', views.topic_toggle, name='topic_toggle'),
]