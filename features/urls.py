from django.urls import path
from . import views

app_name = 'features'

urlpatterns = [
    path('admin-dashboard/', views.patent_admin_dashboard, name='admin_dashboard'),
    path('api/dashboard-data/', views.api_dashboard_data, name='api_dashboard_data'),
]
