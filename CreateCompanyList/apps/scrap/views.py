# -*- coding: utf-8 -*-

from rest_framework import generics
from rest_framework.response import Response

from django.shortcuts import render

from apps.scrap.models import CompanyList


# class CompanyListViewSet(generics.ListCreateAPIView):
#     queryset = CompanyList.objects.all()
#     serializer_class = CompanyListSerializer
#     lookup_field = 'uuid'


#     def list(self, request):
#         queryset = self.get_queryset()
#         serializer = CompanyListSerializer(queryset, many=True)
#         return Response(serializer.data)
