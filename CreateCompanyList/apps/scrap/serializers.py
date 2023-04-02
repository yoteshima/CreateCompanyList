# -*- coding: utf-8 -*-

from rest_framework import serializers
from apps.scrap.models import CompanyList


class CompanyListSerializer(serializers.ModelSerializer):
    """
    会社リスト用のシリアライザ
    """
    class Meta:
        model = CompanyList
        fields = ('uuid', 'company', 'user', 'status', )