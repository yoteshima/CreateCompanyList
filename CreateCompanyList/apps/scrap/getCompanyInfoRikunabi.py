# -*- coding: utf-8 -*-

import re
from typing import List, Union, Tuple

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver
from selenium.webdriver.common.by import By

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoRikunabi(GetCompanyInfoMixin):
    """
    リクナビから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    KAKKO_PTN = r"(.+)(【|（|「)(.*(会社|株|有).*)(】|）|」)"
    # 不要な文字列から会社の名称のみを抽出するためのパターン
    COMPANY_NAME_PTN = r"([^\s★◆]*(会社|株|有)[^\s★◆]*)"
    # キーワードフィルタ
    KEYWOED = ["IT", "DX", "デジタル", "社内SE", "テクニカル", "アプリ", "システム開発", "ソフトウェア開発"]

    def __init__(
        self,
        interval: int = 5,
        purge_domein_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(
                base_url="https://next.rikunabi.com",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        self.keyword = kwargs.get("keyword", "")
        # 検索用URLを作成
        self.SEARCH_PAGE_URL = "{url}/rnc/docs/cp_s00890.jsp?leadtc=n_ichiran_panel_submit_btn"\
                    .format(url=self.BASE_URL)


    def _cleansing_company_name(
        self,
        company_element: Union[ChromeWebDriver, FirefoxWebDriver]
    ) -> str:
        company_name = company_element.text
        matched = re.match(self.COMPANY_NAME_PTN, company_name)
        if matched:
            return matched.group(1)
        matched = re.match(self.KAKKO_PTN, company_name)
        if matched:
            return matched.group(3)
        return company_name


    def _get_pure_company_name(
        self,
        company_element: Union[ChromeWebDriver, FirefoxWebDriver]
    ) -> str:
        try:
            company_link_element = company_element.find_element(By.TAG_NAME, "a")
            c_link = company_link_element.get_attribute('href')
            soup = self.parse_html(url_=c_link)
            breadcrumb = soup.find("ul", class_="rnn-breadcrumb")
            return breadcrumb.text.splitlines()[-1]
        except:
            return company_element.text


    def _is_filtered_keyword(
        self,
        discripts: List[Union[ChromeWebDriver, FirefoxWebDriver]]
    ) -> bool:
        for discript in discripts:
            for key in self.KEYWOED:
                if key in discript.text:
                    return True
        return False


    def get_next_page_url(self, driver: Union[ChromeWebDriver, FirefoxWebDriver]) -> str:
        try:
            next_page_element = driver.find_element(By.CLASS_NAME, "rnn-pagination__next")
            next_page_link_element = next_page_element.find_element(By.TAG_NAME, "a")
            return next_page_link_element.get_attribute('href')
        except Exception as e:
            print("最終ページです。")
            print(e)


    def _search_keyword(self, driver: Union[ChromeWebDriver, FirefoxWebDriver]) -> Union[ChromeWebDriver, FirefoxWebDriver]:
        # ページのキーワード検索する
        input_keyword_element = driver.find_element(By.CLASS_NAME, "rn3-conditionKeywordInput__input")
        input_keyword_element.send_keys(self.keyword)
        # 検索ボタンを押下
        search_button_element = driver.find_element(By.CLASS_NAME, "rn3-sideConditionalSearch__buttonSearch")
        search_button_element.click()

        return driver


    def _create_company_name_list(
        self,
        driver: Union[ChromeWebDriver, FirefoxWebDriver],
        output_list: List[str] = []
    ) -> Tuple[Union[ChromeWebDriver, FirefoxWebDriver, List[str]]]:
        # 会社情報一覧を取得
        company_element_list = driver.find_elements(By.CLASS_NAME, "rnn-jobOfferList__item")
        company_name_list = []
        for company_element in company_element_list:
            # 会社名欄
            c_name_element = company_element.find_element(By.CLASS_NAME, "rnn-jobOfferList__item__company__text")
            # 仕事の概要欄
            c_disc_elements = company_element.find_elements(By.CLASS_NAME, "rnn-offerDetail__text")
            if self._is_filtered_keyword(discripts=c_disc_elements):
                c_name = self._get_pure_company_name(company_element=c_name_element)
                if c_name not in company_name_list \
                                    and c_name not in output_list:
                    print(f"company name: {c_name}")
                    company_name_list.append(c_name)
        return driver, company_name_list


    def execute(
        self,
        output_filename: str = "./temp.txt",
        output_flg: bool = False
    ) -> List[str]:
        """
        会社名リスト作成を実行
        """
        print("started process")
        output_company_list = []
        try:
            # トップページを表示
            driver = self.init_selenium_ff_get_page(url_=self.SEARCH_PAGE_URL)
            # キーワードでサイト内検索
            driver = self._search_keyword(driver=driver)
            url = ""
            while True:
                if url:
                    # URL
                    print(f"accsess url: {url}")
                    # 会社一覧ページをパース
                    driver = self.init_selenium_ff_get_page(url_=url)
                driver, company_list = self._create_company_name_list(
                                    driver=driver, output_list=output_company_list)
                # 会社名のリスト
                output_company_list.extend(company_list.copy())
                #次のページURLを取得
                url = self.get_next_page_url(driver=driver)
                print(f"next page url: {url}")
                # 毎回ブラウザを閉じる
                driver.close()
        except Exception as e:
            print(e)

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        return output_company_list


if __name__ == "__main__":
    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='リクナビNEXTから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="IT")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="./temp_rikunabi_next.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="./temp_dict_rikunabi_next.csv")
    args = parser.parse_args()
    # 引数の取得
    keyword = args.keyword
    interval = args.interval
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    get_company_info = None

    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoRikunabi(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(output_filename=output_filename_text, output_flg=output_flg)
    get_company_info.create_company_info(conmpany_name_list=company_list, source="リクナビNEXT", output_filename=output_filename_csv, output_flg=output_flg)
