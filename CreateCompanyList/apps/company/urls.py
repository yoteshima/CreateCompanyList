# -*- coding: utf-8 -*-s

from django.urls import path
from apps.company import views


urlpatterns = [
    path('', views.CompanyViewSet.as_view(), name='company_view_set_list'),
]