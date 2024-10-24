# -*- coding: utf-8 -*-

import re
import os
from typing import List, Union, Tuple
from datetime import datetime

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoGeekly(GetCompanyInfoMixin):
    """
    Geeklyから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = r"^(.+)（.+）$"


    def __init__(
        self,
        interval: int = 5,
        purge_domein_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(
                base_url="https://www.geekly.co.jp",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        limit = kwargs.get("limit", "")
        sort = kwargs.get("sort", "")
        # 検索表示数
        parts_limit = ""
        if limit:
            parts_limit = f"limit:{limit}/"
        # 並び替え順
        parts_sort = ""
        if sort == "年収が高い順":
            parts_sort = "sort:nensyu_max/"
        elif sort == "新着順":
            parts_sort = "sort:new_flg/"
        elif sort == "おすすめ順":
            parts_sort = "sort:kodawari_count/"
        # 検索用URLを作成
        self.SEARCH_PAGE_URL = f"{self.BASE_URL}/search/joblist/{parts_limit}{parts_sort}direction:desc"


    def _remove_other_company_name(self, company_name: str) -> str:
        """
        会社名のみを取得
        """
        # 会社名を取得
        c_name = company_name
        # （）などの余計な文字列を削除
        result = re.match(self.PTN, c_name)
        if result:
            # （）書きは削除
            c_name = result.group(1)
        return c_name


    def _create_company_name_list(self, url_: str, output_list: List[str]) -> Tuple[List[str], str]:
        # 会社一覧ページをパース
        company_name_list = []
        driver = self.init_selenium_ff_get_page(url_=url_)
        # 会社名の一覧のエレメントを取得
        company_name_elements = driver.find_elements(By.XPATH, '//div[@class="company_name"]/a')
        for c_name_element in company_name_elements:
            company_name_text = c_name_element.text
            # 会社名の後に続く不要な文言を削除
            # conpany_name_text = self._remove_other_company_name(company_name=conpany_name_text)
            if company_name_text not in company_name_list \
                            and company_name_text not in output_list:
                print(f"company name: {company_name_text}")
                # 重複なし
                company_name_list.append(company_name_text)
        # 次のページURLを取得
        nextpage = self._get_next_page_url(driver=driver)
        return company_name_list, nextpage


    def _get_next_page_url(self, driver: Union[ChromeWebDriver, FirefoxWebDriver]) -> str:
        """
        次のページ用のURLを取得
        """
        p_next = None
        try:
            # 次のページのエレメントを取得
            p_next = driver.find_element(By.XPATH, '//li[@class="pager_next"]/a')
            # paging_element = driver.find_element(By.CLASS_NAME, "pager_next")
            # p_next = paging_element if ">" in paging_element.text else None
        except:
            pass
        nextpage = ""
        if p_next:
            # 次のページのURLが存在する
            nextpage = p_next.get_attribute("href")
            print(f"next page: {nextpage}")
        # ドライバを閉じる
        driver.close()
        return nextpage


    def execute(
        self,
        source: str = "Geekly",
        output_filename: str = "./temp.txt",
        output_filename_csv: str = "./temp.csv",
        output_flg: bool = False,
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
            # 次のページURL取得
            while next_url:
                c_name_list, next_url = self._create_company_name_list(
                    url_=next_url,
                    output_list=output_company_list
                )
                output_company_list.extend(c_name_list)
                if not next_url:
                    # 次のページがない場合、ループ終了
                    print("This is the last page.")
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
    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='Geeklyから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="IT")
    parser.add_argument("--limit", type=str, help="媒体サイト内での表示数", default="50")
    parser.add_argument("--sort", type=str, help="媒体サイト内でのソート順", default="年収が高い順")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="temp_geekly.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="temp_dict_geekly.csv")
    args = parser.parse_args()
    # 引数の取得
    keyword = args.keyword
    limit = args.limit
    sort = args.sort
    interval = args.interval
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoGeekly(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list, limit=limit, sort=sort)
    company_list = get_company_info.execute(
        source="Geekly",
        output_filename=output_filename_text,
        output_filename_csv=output_filename_csv,
        output_flg=output_flg
    )
