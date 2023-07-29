# -*- coding: utf-8 -*-

import uuid
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.account.models import User
from apps.company.models import Company
from apps.scrap import utils

# 会社リストのステータス選択肢
COMPANY_LIST_STATUS = utils.COMPANY_LIST_STATUS


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
    user = models.ForeignKey(verbose_name=_('charge'),
                to=User, on_delete=models.DO_NOTHING, null=True, blank=True)
    status = models.CharField(verbose_name=_('statua'),
                choices=COMPANY_LIST_STATUS, max_length=1, 
                        default=COMPANY_LIST_STATUS[0][0])


    def __str__(self):
        return '{} {}'.format(
                self.company.name, self.company.url)