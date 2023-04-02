# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from apps.company.models import Company
from apps.scrap import scrapCompanyInfo
from apps.scrap.models import CompanyList

import logging
logger = logging.getLogger(__name__)

# 未連絡
NO_CONTACT = 0

class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        # 会社リスト
        company_list = []
        # 除外ドメインリスト
        purge_domein_list = []
        # 各媒体サイトから情報を取得
        try:
            # @typeから企業情報を取得
            get_company_info_type = scrapCompanyInfo.GetCompanyInfoType(
                                    keyword="IT", purge_domein_list=purge_domein_list)
            company_list.extend(get_company_info_type.execute())
        except:
            logger.error('@typeより情報を取得するのに失敗しました。')
        
        try:
            # Greenから企業情報を取得
            get_company_info_green = scrapCompanyInfo.GetCompanyInfoGreen(
                                    keyword="IT", purge_domein_list=purge_domein_list)
            company_list.extend(get_company_info_green.execute())
        except:
            logger.error('Greenより情報を取得するのに失敗しました。')
        
        # 会社情報を保存
        for clist in company_list:
            name = clist[0]
            url = clist[1]
            if not Company.objects.filter(name=name).exists():
                # 会社名に被りがないものだけ登録
                company = Company.objects.create(name=name, url=url)
                # 会社リストを作成
                CompanyList.objects.create(company=company, status=NO_CONTACT)
            else:
                logger.info('会社名: {}はすでに登録済みです。スキップします。'.format(name))
                continue

