# -*- coding: utf-8 -*-

import re
from typing import List

from selenium.webdriver.common.by import By

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoOpenwork(GetCompanyInfoMixin):
    """
    openworkから企業情報を取得するクラス
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
                base_url="https://www.openwork.jp",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        keyword = kwargs.get("keyword")
        if keyword:
            # 検索用URLを作成
            self.SEARCH_PAGE_URL = "{url}/company_list?field=0023&pref=&src_str=&sort=1"\
                        .format(url=self.BASE_URL)
        else:
            # キーワードなしエラー
            pass


    def _remove_other_company_name(self, company_name: str) -> str:
        """
        会社名のみを取得
        """
        # 会社名をスペースで分離
        # company_name_list = company_name.split()
        # 会社名を取得
        # c_name = company_name_list.pop(0)
        c_name = company_name
        # （）などの余計な文字列を削除
        result = re.match(self.PTN, c_name)
        if result:
            # （）書きは削除
            c_name = result.group(1)
        return c_name


    def _create_company_name_list(self, url_: str, output_list: List[str]) -> List[str]:
        # 会社一覧ページをパース
        company_name_list = []
        driver = self.init_selenium_ff_get_page(url_=url_)
        # 会社名の一覧のエレメントを取得
        company_name_elements = driver.find_elements(By.CLASS_NAME, "searchCompanyName")
        for company_name_element in company_name_elements:
            c_name_element = company_name_element.find_element(By.XPATH, ".//div/h3/a")
            if c_name_element:
                # 会社名がnullではない
                conpany_name_text = c_name_element.text
                # 会社名の後に続く不要な文言を削除
                conpany_name_text = self._remove_other_company_name(company_name=conpany_name_text)
                if conpany_name_text not in company_name_list \
                                and conpany_name_text not in output_list:
                    print(f"company name: {conpany_name_text}")
                    # 重複なし
                    company_name_list.append(conpany_name_text)
        driver.close()
        return company_name_list


    def _get_next_page_url(self, url_: str) -> str:
        """
        次のページ用のURLを取得
        """
        driver = self.init_selenium_ff_get_page(url_=url_)
        # 次のページのエレメントを取得
        paging_elements = driver.find_elements(By.CLASS_NAME, "paging_link-more")
        p_next = None
        for paging_element in paging_elements:
            p_next = paging_element if "次へ" == paging_element.text else None
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
        output_filename: str = "./temp.txt",
        output_flg: bool = False
    ) -> List[str]:
        """
        会社名リスト作成を実行
        """
        # Slack通知
        self.slack_client.post_message(
            source="openwork",
            message="処理を開始します。"
        )
        output_company_list = []
        try:
            # 検索ページトップ画面の一覧から会社名を取得
            c_name_list = self._create_company_name_list(
                        url_=self.SEARCH_PAGE_URL, output_list=output_company_list)
            output_company_list.extend(c_name_list)
            # 次のページURL取得
            next_url = self._get_next_page_url(url_=self.SEARCH_PAGE_URL)
            while next_url:
                output_company_list.extend(
                        self._create_company_name_list(
                                url_=next_url, output_list=output_company_list).copy())
                # 次のページURL取得
                next_url = self._get_next_page_url(url_=next_url)
                if not next_url:
                    # 次のページがない場合、ループ終了
                    print("This is the last page.")
                    break
        except Exception as e:
            import traceback
            # Slack通知
            self.slack_client.post_message(
                source="openwork",
                message=traceback.format_exc(),
                status="warn"
            )

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        # Slack通知
        self.slack_client.post_message(
            source="openwork",
            message=f"媒体から会社名の取得が完了しました。 {len(output_company_list)} 件"
        )
        return output_company_list


if __name__ == "__main__":
    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='openworkから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="IT")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="./temp_openwork.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="./temp_dict_openwork.csv")
    args = parser.parse_args()
    # 引数の取得
    keyword = args.keyword
    interval = args.interval
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoOpenwork(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(output_filename=output_filename_text, output_flg=output_flg)
    get_company_info.create_company_info(conmpany_name_list=company_list, source="openwork", output_filename=output_filename_csv, output_flg=output_flg)
