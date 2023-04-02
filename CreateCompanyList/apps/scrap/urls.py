# -*- coding: utf-8 -*-s

from django.urls import path
from apps.scrap import views


urlpatterns = [
    path('', views.CompanyListViewSet.as_view(), name='company_list_view_set_list'),
]