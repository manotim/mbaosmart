from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Accounts URLs (Authentication)
    path('accounts/', include('accounts.urls')),
    
    # Dashboard/Home Page (if you have one)
    # path('', include('dashboard.urls')),  # Uncomment if you have dashboard app
    
    # Procurement URLs
    path('procurement/', include('procurement.urls')),
    
    # Production URLs
    path('production/', include('production.urls')),
    
    # Inventory URLs
    path('inventory/', include('inventory.urls')),
    # HR URLS
    path('hr/', include('hr.urls')),
]
# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)