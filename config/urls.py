"""URL configuration for config project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve
from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.landing_page, name='landing'),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')), # Allauth routes
    path('courses/', include('courses.urls')),
    path('ai/', include('ai_engine.urls')),
    path('quizzes/', include('quizzes.urls')),
    path('', include('accounts.urls')),  
    path('dashboard/', include('dashboard.urls')),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]