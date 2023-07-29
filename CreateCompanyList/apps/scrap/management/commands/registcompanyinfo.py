# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from apps.company.models import Company
from apps.scrap import scrapCompanyInfo
from apps.scrap.models import CompanyList

import traceback
import logging
logger = logging.getLogger(__name__)

# 未連絡
NO_CONTACT = 0

class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        logger.info('処理を開始します。')
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
            self.seve_company_data(company_list=company_list, instance_=get_company_info_type)
        except Exception as err_type:
            logger.error('Greenより情報を取得するのに失敗しました。', err_type)
            logger.error(traceback.format_stack())
        
        try:
            # Greenから企業情報を取得
            get_company_info_green = scrapCompanyInfo.GetCompanyInfoGreen(
                                    keyword="IT", purge_domein_list=purge_domein_list)
            company_list.extend(get_company_info_green.execute())
            self.seve_company_data(company_list=company_list, instance_=get_company_info_green)
        except Exception as err_green:
            logger.error('Greenより情報を取得するのに失敗しました。', err_green)
            logger.error(traceback.format_stack())
        logger.info('処理を終了します。')


    def seve_company_data(self, company_list, instance_):
        # 会社情報を保存
        for cname in company_list:
            if not Company.objects.filter(name=cname).exists():
                # 会社のURLを取得
                company_info = instance_.get_company_url(conmapny_name=cname)

                # 会社名に被りがないものだけ登録
                company = Company.objects.create(
                                name=company_info['name'], url=company_info['url'])
                # 会社リストを作成
                CompanyList.objects.create(company=company, status=NO_CONTACT)
            else:
                logger.info('会社名: {}はすでに登録済みです。スキップします。'.format(cname))
                continue

