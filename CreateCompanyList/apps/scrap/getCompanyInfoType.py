# -*- coding: utf-8 -*-

import os
import re
from typing import List
from datetime import datetime

from scrapCompanyInfo import GetCompanyInfoMixin


class GetCompanyInfoType(GetCompanyInfoMixin):
    """
    @typeから企業情報を取得するクラス
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
                base_url="https://type.jp",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        keyword = kwargs.get("keyword")
        if keyword:
            # 検索用URLを作成
            self.SEARCH_PAGE_URL = "{url}/job/search.do?/keyword={keyword}"\
                        .format(url=self.BASE_URL, keyword=keyword)
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
        soup = self.parse_html(url_=url_)
        company_name_list = []
        for elem in soup.find_all("p", class_="company"):
            company_name = elem.find("span")
            if company_name:
                # 会社名がnullではない
                conpany_name_text = company_name.text
                # 会社名以外の文字列を削除
                conpany_name_text = self._remove_other_company_name(conpany_name_text)
                if conpany_name_text not in company_name_list \
                                and conpany_name_text not in output_list:
                    print(f"company name: {conpany_name_text}")
                    # 重複なし
                    company_name_list.append(conpany_name_text)
        return company_name_list


    def _get_next_page_url(self, url_: str) -> str:
        """
        次のページ用のURLを取得
        """
        soup = self.parse_html(url_=url_)
        p_next = soup.find("p", class_="next").find("a")
        nextpage = ""
        if p_next:
            # 次のページのURLが存在する
            nextpage = p_next.get("href")
        if nextpage:
            # 基となるURLと次ページのURLを合わせる
            nextpage = "{base_url}{next}"\
                .format(base_url=self.BASE_URL, next=nextpage)
        print(f"next page: {nextpage}")
        return nextpage


    def execute(
        self,
        source: str = "@type",
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
    parser = argparse.ArgumentParser(description='@typeから会社の情報を取得する')
    parser.add_argument("--keyword", type=str, help="媒体サイト内での検索キーワード", default="IT")
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="temp_type.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="temp_dict_type.csv")
    args = parser.parse_args()
    # 引数の取得
    keyword = args.keyword
    interval = args.interval
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    company_list = []
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoType(keyword=keyword, interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(
        source="@type",
        output_filename=output_filename_text,
        output_filename_csv=output_filename_csv,
        output_flg=output_flg
    )
