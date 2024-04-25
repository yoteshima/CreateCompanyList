# -*- coding: utf-8 -*-

import time
import random
from typing import List, Union, Tuple

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoFuma(GetCompanyInfoMixin):
    """
    FUMAから企業情報を取得するクラス
    """
    # 取得するページ数
    GET_PAGE_NUM = 10

    def __init__(
        self,
        interval: int = 5,
        purge_domein_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(
                base_url="https://fumadata.com",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        self.keyword = kwargs.get("keyword", "")
        # 検索用URLを作成
        self.SEARCH_PAGE_URL = "{url}/search?fromtop=1&dai_code[]=G&chu_code[]=39&titledata={keyword}"\
                    .format(url=self.BASE_URL, keyword=self.keyword)


    def generate_interval(self, min: int = 60, max: int = 300) -> int:
        return random.randint(min, max)


    def _get_company_details(self, url_: str) -> Tuple[str]:
        # 会社の詳細を取得
        url = capital = employee = ""
        # 企業詳細ページを展開
        driver = self.init_selenium_ff_get_page(url_=url_)
        company_detail_data_element = driver\
                .find_element(By.CLASS_NAME, "detail_kigyou_data")
        # 企業用のHPのURLを取得
        url = company_detail_data_element\
                .find_element(By.CLASS_NAME, "a_text").text
        # 企業データ用のテーブル情報を取得
        company_data_tr_elements = company_detail_data_element\
                .find_elements(By.XPATH, ".//tr")

        for tr in company_data_tr_elements:
            th_elements = tr.find_elements(By.XPATH, ".//th")

            for i, th_element in enumerate(th_elements):
                # 各情報を取得
                if "資本金" in th_element.text:
                    capital = tr.find_elements(By.XPATH, ".//td")[i].text
                if  "従業員数" in th_element.text:
                    employee = tr.find_elements(By.XPATH, ".//td")[i].text

        driver.close()
        return url, capital, employee


    def _create_company_name_list(
        self,
        driver: Union[ChromeWebDriver, FirefoxWebDriver],
        output_list: List[str] = []
    ) -> List[List[Union[str, int]]]:
        # 現在のページ数を取得
        paging_box_element = driver.find_element(By.CLASS_NAME, "paging_box")
        current_page_element = paging_box_element.find_element(By.XPATH, ".//div/span/strong")
        c_page = current_page_element.text
        # 会社情報一覧を取得
        company_box_element_list = driver.find_elements(By.CLASS_NAME, "s_box")
        company_name_list = []
        c_name = ""
        for company_box_element in company_box_element_list:
            # 会社名取得
            company_name_element = company_box_element.find_element(By.CLASS_NAME, "s_coprate")
            c_name = company_name_element.text
            company_info_element = company_box_element.find_element(By.CLASS_NAME, "fl_box")
            company_info_list_element = company_info_element.find_elements(By.XPATH, ".//li")
            c_capital = c_employee = ""
            for company_info in company_info_list_element:
                if "資本金" in company_info.text:
                    c_capital = company_info.text.lstrip("資本金：")
                elif "従業員数" in company_info.text:
                    c_employee = company_info.text.lstrip("従業員数：")
            
            if c_name not in company_name_list \
                            and c_name not in output_list:
                # 会社名の重複なし
                company_name_list.append([c_name, c_capital, c_employee, c_page])

        return company_name_list


    def execute(
        self,
        target_page: int = 0,
        output_filename: str = "./temp.txt",
        output_flg: bool = False
    ) -> List[Union[str, int]]:
        """
        会社名リスト作成を実行
        """
        output_company_list = []
        cnt = 0
        while cnt < self.GET_PAGE_NUM:
            print(f"started main process: ({cnt+1}/{self.GET_PAGE_NUM})")
            # 前回まで登録したページを取得
            page = 0
            if target_page:
                page = target_page
            else:
                page = self.get_page()
            page_url = ""
            if page:
                # ページ用のURLを生成
                next_page_num = page * 50
                page_url = f"&num={next_page_num}"
            search_page_url = self.SEARCH_PAGE_URL + page_url
            print(f"access page: {search_page_url}")
            try:
                driver = self.init_selenium_ff_get_page(url_=search_page_url)
                output_company_list.extend(self._create_company_name_list(
                        driver=driver, output_list=output_company_list).copy())
                
                if cnt <= self.GET_PAGE_NUM:
                    # 次のページ
                    target_page += 1
                    # ランダムにインターバルを挟む
                    interval = self.generate_interval()
                    print(f"wait: {interval} sec")
                    time.sleep(interval)
                cnt += 1
                # ブラウザを閉じる
                driver.close()
            except Exception as e:
                print(f"error: {e}")
                break

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_datas(filename_=output_filename,
                    data_list=output_company_list)
        return output_company_list


if __name__ == "__main__":
    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='Fumaから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="情報サービス業")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--page", type=int, help="取得を開始するページ数", default=None)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="./temp_fuma.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="./temp_dict_fuma.csv")
    args = parser.parse_args()
    # 引数の取得
    keyword = args.keyword
    interval = args.interval
    page = args.page
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoFuma(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(target_page=page, output_filename=output_filename_text, output_flg=output_flg)
    get_company_info.create_company_infos(conmpany_name_list=company_list, source="Fuma", output_filename=output_filename_csv, output_flg=output_flg)
