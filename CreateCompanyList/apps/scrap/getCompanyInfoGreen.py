# -*- coding: utf-8 -*-

from typing import List

from selenium.webdriver.common.by import By

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoGreen(GetCompanyInfoMixin):
    """
    Greenから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = "(.+)(【|（)(.+)(】|）)"


    def __init__(
        self,
        interval: int = 5,
        purge_domein_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        super().__init__(
                base_url="https://www.green-japan.com",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        keyword = kwargs.get("keyword")
        if keyword:
            # 検索用URLを作成
            self.SEARCH_PAGE_URL = "{url}/search_key?keyword={keyword}"\
                        .format(url=self.BASE_URL, keyword=keyword)
        else:
            # キーワードなしエラー
            pass


    def _create_company_name_list(self, url_: str, output_list: List[str]) -> List[str]:
        # 会社一覧ページをパース
        soup = self.parse_html(url_=url_)
        company_name_list = []
        for company_name in soup.find_all("div", class_="MuiTypography-subtitle2"):
            if company_name:
                # 会社名がnullではない
                conpany_name_text = company_name.text
                if conpany_name_text not in company_name_list \
                                and conpany_name_text not in output_list:
                    # 重複なし
                    company_name_list.append(conpany_name_text)
        return company_name_list


    def _get_next_page_url(self, url_: str) -> str:
        """
        次のページ用のURLを取得
        """
        driver = self.init_selenium_ff_get_page(url_=url_)
        selected_page_element = driver.find_element(By.CLASS_NAME, "Mui-selected")
        curr_page = selected_page_element.text
        next_page_href = f"/search?page={int(curr_page)+1}"

        next_page_element = driver.find_element(By.CSS_SELECTOR, f'a[href="{next_page_href}"]')
        nextpage = ""
        if next_page_element:
            # 次のページがあれば
            nextpage = next_page_href
        if nextpage:
            # 基となるURLと次ページのURLを合わせる
            nextpage = "{base_url}{next}"\
                .format(base_url=self.BASE_URL, next=nextpage)
        # ブラウザを閉じる
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
            source="Green",
            message="処理を開始します。"
        )
        output_company_list = []
        # 検索ページトップ画面の一覧から会社名を取得
        c_name_list = self._create_company_name_list(
                    url_=self.SEARCH_PAGE_URL, output_list=output_company_list)
        output_company_list.extend(c_name_list)
        # 次のページURL取得
        next_url = self._get_next_page_url(url_=self.SEARCH_PAGE_URL)
        print(f"次のURL：{next_url}")
        while next_url:
            try:
                output_company_list.extend(
                        self._create_company_name_list(
                                url_=next_url, output_list=output_company_list).copy())
                # 次のページURL取得
                next_url = self._get_next_page_url(url_=next_url)
                if not next_url:
                    # 次のページがない場合、ループ終了
                    break
                print(f"次のURL：{next_url}")
            except:
                print("最終ページです。")
                break

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        # Slack通知
        self.slack_client.post_message(
            source="Green",
            message=f"媒体から会社名の取得が完了しました。 {len(output_company_list)} 件"
        )
        return output_company_list


if __name__ == "__main__":
    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='Greenから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="IT")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="./temp_green.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="./temp_dict_green.csv")
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

    get_company_info = GetCompanyInfoGreen(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(output_filename=output_filename_text, output_flg=output_flg)
    get_company_info.create_company_info(company_name_list=company_list, source="Green", output_filename=output_filename_csv, output_flg=output_flg)
