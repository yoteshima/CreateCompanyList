# -*- coding: utf-8 -*-

import os
import re
import time

from datetime import datetime
from enum import Enum
from typing import List, Tuple, Union
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver

from scrapCompanyInfo import GetCompanyInfoMixin
from common.utils.utils import generate_interval
from common.decorater.wait_sec import wait_seconds

class IndustoryType(Enum):
    industory_14 = (14, "Webサービス", "IT・通信")
    industory_15 = (15, "ソフトウェア", "IT・通信")
    industory_16 = (16, "情報処理", "IT・通信")
    industory_17 = (17, "インターネット附随サービス業", "IT・通信")
    industory_18 = (18, "その他", "IT・通信")
    industory_34 = (34, "通信業", "IT・通信")


    def __init__(
        self, 
        id: int,
        title: str,
        industory_type: str
    ) -> None:
        self.id = id
        self.title = title
        self.industory_type = industory_type

    @classmethod
    def get_id_by_name(cls, title):
        for item in cls:
            if item.title == title:
                return item.id
        return None


class PrefectureType(Enum):
    prefecture_11 = (11, "埼玉県", "関東")
    prefecture_12 = (12, "千葉県", "関東")
    prefecture_13 = (13, "東京都", "関東")
    prefecture_14 = (14, "神奈川県", "関東")

    def __init__(
        self,
        id: int,
        prefecture: str,
        area: str
    ) -> None:
        self.id = id
        self.prefecture = prefecture
        self.area = area

    @classmethod
    def get_id_by_name(cls, prefecture):
        for item in cls:
            if item.prefecture == prefecture:
                return item.id
        return None


class GetCompanyInfoSyukatsuKaigi(GetCompanyInfoMixin):
    """
    就活会議から企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = "(.+)(【|（)(.+)(】|）)"

    def __init__(
        self,
        interval: int = 5,
        purge_domein_list: List[str] = [],
        industory_list: List[str] = [],
        prefecture_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(
                base_url="https://syukatsu-kaigi.jp",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        url_parts = ""
        for industory_name in industory_list:
            # 業界名を取得
            industory_id = IndustoryType.get_id_by_name(title=industory_name)
            # for prefecture_name in prefecture_list:
            #     prefecture_id = PrefectureType.get_id_by_name(prefecture=prefecture_name)
            url_parts = url_parts + f"company_form[industry_middle_id][]={industory_id}&"
        # 検索用URLを作成
        self.SEARCH_PAGE_URL = "{url}/companies/search?{parts}"\
            .format(
                url=self.BASE_URL,
                parts=url_parts
            )


    def _remove_extra_phrases(self, company_name: str) -> str:
        """
        会社名の付与されている(旧: ××)のような文言を削除
        """
        pattern = r'^(.*?)（.*?）$'
        matched = re.match(pattern, company_name)

        if matched:
            return matched.group(1)
        return company_name


    def _create_company_name_list(
        self,
        url_: str,
        output_list: List[str] = []
    ) -> Tuple[List[str], str]:
        company_name_list = []
        # 企業詳細ページを展開
        driver = self.init_selenium_ff_get_page(url_=url_)
        company_name_elements = driver\
                .find_elements(By.CLASS_NAME, "p-search-panel__heading")
        # 余計な文言を取り除いた会社名でリストを作成
        for company_name_element in company_name_elements:
            company_name = company_name_element.text
            if company_name not in output_list:
                # サイト内での会社名の被らない物のみリストに追加
                company_name_list.append(company_name)
                print(f"company_name: {company_name}")
        nextpage = self._get_next_page_url(driver=driver)
        # Webドライバを閉じる
        # driver.close()
        return company_name_list, nextpage


    def _get_next_page_url(
        self,
        driver: Union[ChromeWebDriver, FirefoxWebDriver]
    ) -> None:
        """
        次のページ用のURLを取得
        """
        try:
            # ページャURL全件取得
            pager_list_element = driver.find_element(
                By.XPATH, '//li[@class="next"]/a'
            )
            nextpage = pager_list_element.get_attribute("href")
        except:
            print("最終ページです。")
            nextpage = ""

        print(f"next page url: {nextpage}")
        driver.close()
        return nextpage


    def execute(
        self,
        source: str = "就活会議",
        output_filename: str = "./temp.txt",
        output_filename_csv: str = "./temp.csv",
        output_flg: bool = False
    ) -> List[str]:
        """
        会社名リスト作成を実行
        """
        # Slack通知
        self.slack_client.post_message(
            source=source,
            message="処理を開始します。"
        )
        output_company_list = []
        try:
            # 検索ページトップ画面の一覧から会社名を取得
            c_name_list, next_url = self._create_company_name_list(
                        url_=self.SEARCH_PAGE_URL, output_list=output_company_list)
            output_company_list.extend(c_name_list)
            while next_url:
                interval = generate_interval()
                print(f"wait: {interval} sec")
                time.sleep(generate_interval())
                c_name_list, next_url = self._create_company_name_list(
                    url_=next_url,
                    output_list=output_company_list
                )
                output_company_list.extend(c_name_list.copy())
                print(f"out put companys name: {output_company_list}")
                if not next_url:
                    # 次のページがない場合、ループ終了
                    break
        except Exception as e:
            import traceback
            # Slack通知
            self.slack_client.post_message(
                source=source,
                message=traceback.format_exc(),
                status="warn"
            )

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        # Slack通知
        self.slack_client.post_message(
            source=source,
            message=f"媒体から会社名の取得が完了しました。 {len(output_company_list)} 件"
        )
        # 取得した会社名リストにHPのURLを付与したデータをDBへ登録
        _ = self.create_company_info(
            company_name_list=output_company_list,
            source=source,
            output_filename=output_filename_csv,
            output_flg=output_flg
        )
        # 出力用ファイル名を設定
        output_filename_list: List[str] = output_filename_csv.split(".")
        today: str = datetime.now().strftime('%Y%m%d')
        output_filepath: str = os.path.join(
            self.OUTPUT_DIR,
            f"{output_filename_list[0]}_{today}.{output_filename_list[-1]}"
        )
        # DBからCSVを出力
        self.output_csv_from_db(
            filename=output_filepath,
            source=source
        )
        # Slackへ出力したデータ送信
        self.slack_file_client.upload_files(
            csv_file_path=output_filepath,
            filename=output_filename_csv,
            title=f"{source}から取得した情報"
        )
        return output_company_list


if __name__ == "__main__":

    def str_to_list(arg):
        return arg.split(',')

    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='就活会議から会社の情報を取得する')
    parser.add_argument("--industory-list", type=str_to_list, help="媒体サイト内での業界名リスト", default=[])
    parser.add_argument("--prefecture-list", type=str_to_list, help="媒体サイト内での都道府県名リスト", default=[])
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="temp_syukatsu_kaigi.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="temp_dict_syukatsu_kaigi.csv")
    args = parser.parse_args()
    # 引数の取得
    industory_list = args.industory_list
    prefecture_list = args.prefecture_list
    interval = args.interval
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    purge_domein_list = ['wantedly.com']

    if not industory_list:
        industory_list = [
            "Webサービス",
            "ソフトウェア",
            "情報処理",
            "インターネット附随サービス業",
            "その他",
            "通信業"
        ]
    if not prefecture_list:
        prefecture_list = [
            "埼玉県",
            "千葉県",
            "東京都",
            "神奈川県"
        ]

    get_company_info = GetCompanyInfoSyukatsuKaigi(industory_list=industory_list, prefecture_list=prefecture_list, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(
        source="就活会議",
        output_filename=output_filename_text,
        output_filename_csv=output_filename_csv,
        output_flg=output_flg
    )
