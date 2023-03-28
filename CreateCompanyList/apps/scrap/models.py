# -*- coding: utf-8 -*-

import uuid
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.account.models import User
from apps.company.models import Company


def set_default_company():
    """
    外部キーのデフォルト値を設定
    """
    default_company = Company.objects.get_or_create(name=_('default company'))
    return default_company


class modelBase(models.Model):
    """
    モデルのベースクラス
    """
    create_date = models.DateTimeField(
                verbose_name=_('create date'), default=datetime.datetime.now())
    update_date = models.DateTimeField(
                verbose_name=_('update date'), null=True, blank=True)
    delete_flag = models.BooleanField(
                verbose_name=_('delete flag'), default=False)


    class Meta:
        abstract = True


    def delete(self):
        """
        削除処理
        """
        self.delete_flag = True
        self.save()


class CompanyList(modelBase):
    """
    会社リストクラス
    """
    uuid = models.UUIDField(verbose_name=_('uuid'), 
                primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(verbose_name=_('company'),
                to=Company, on_delete=models.CASCADE)
    user = models.ForeignKey(verbose_name=_('user'),
                to=User, on_delete=models.DO_NOTHING)


    def __str__(self):
        return self.comapny.name