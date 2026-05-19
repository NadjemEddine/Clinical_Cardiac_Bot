from django.contrib import admin
from django.urls import path, include 
from django.conf.urls.static import static
from accounts.views import main_view

from .settings import DEBUG, MEDIA_ROOT, MEDIA_URL , STATIC_URL , STATICFILES_DIRS

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', main_view, name='main'),
    # API routes
    path('accounts/', include('accounts.urls')),  # API routes (register, token, refresh, logout)
    path('chatbot/', include('chatbot.urls')),  # API routes (register, token, refresh, logout)
        
]+ static(MEDIA_URL, document_root=MEDIA_ROOT)


# Serve static files in development
if DEBUG:
    urlpatterns += static(STATIC_URL, document_root=STATICFILES_DIRS[0])