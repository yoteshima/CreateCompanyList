# -*- coding: utf-8 -*-

from rest_framework import serializers
from apps.company.models import Company


class CompanySerializer(serializers.ModelSerializer):
    """
    会社リスト用のシリアライザ
    """
    class Meta:
        model = Company
        read_only_fields = ('uuid', )
        fields = ('uuid', 'name', 'url', )