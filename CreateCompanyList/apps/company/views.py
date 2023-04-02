# -*- coding: utf-8 -*-

from rest_framework import generics
from rest_framework.response import Response

from django.shortcuts import render

from apps.company.serializers import CompanySerializer
from apps.company.models import Company


class CompanyViewSet(generics.ListCreateAPIView):
    """
    会社情報を取得するビュークラス
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    lookup_field = 'uuid'


    def list(self, request):
        queryset = self.get_queryset()
        serializer = CompanySerializer(queryset, many=True)
        return Response(serializer.data)