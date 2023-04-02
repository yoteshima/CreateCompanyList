# -*- coding: utf-8 -*-

from rest_framework import generics
from rest_framework.response import Response

from django.shortcuts import render

from apps.company.serializers import CompanySerializer
from apps.company.models import Company


class CompanyViewSet(generics.RetrieveUpdateAPIView):
    """
    会社情報を取得するビュークラス
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    lookup_field = 'uuid'


    def get(self, request, format=None):
        companys = Company.objects.all()
        conpany_info = [{
                'uuid': company.uuid,
                'name': company.name,
                'url': company.url
        } for company in companys if company ]
        
        return Response({'result': conpany_info})
 