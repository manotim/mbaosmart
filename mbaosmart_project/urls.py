"""
URL configuration for mbaosmart_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

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
]