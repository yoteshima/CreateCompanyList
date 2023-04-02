# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

# 会社リストのステータス選択肢
COMPANY_LIST_STATUS = (
    ('0', _('NO CONTACT')),
    ('1', _('CONTACTED')),
    ('9', _('PURGE')),
)