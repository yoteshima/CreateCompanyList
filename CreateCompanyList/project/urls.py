# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v2/company/', include('apps.company.urls')),
    path('v2/scrap/', include('apps.scrap.urls')),
]
