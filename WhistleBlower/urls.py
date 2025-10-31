from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django_admin_kubi import urls

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('admin/', include("django_admin_kubi.urls")),  # Django admin kubi URLS
    path('', include('reports.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin site
admin.site.site_header = " Whistleblowing Admin"
admin.site.site_title = "Whistleblowing System"
admin.site.index_title = "Welcome to Whistleblowing System Administration"