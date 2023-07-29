# -*- coding: utf-8 -*-

import uuid
import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


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


class Company(modelBase):
    """
    会社情報クラス
    """
    uuid = models.UUIDField(verbose_name=_('uuid'), 
                primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(verbose_name=_('company name'), 
                max_length=100, default=_('default company name'))
    url = models.URLField(verbose_name=_('company url'),
                max_length=2083, null=True, blank=True)


    def __str__(self):
        return self.name