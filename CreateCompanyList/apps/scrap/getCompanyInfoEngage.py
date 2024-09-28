# -*- coding: utf-8 -*-

import time

from typing import List, Tuple, Union
from enum import Enum

from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver

from scrapCompanyInfo import GetCompanyInfoMixin
from common.utils.utils import generate_interval


class PrefectureType(Enum):
    hokkaido = ("hokkaido", "北海道")
    aomori = ("aomori", "青森県")
    iwate = ("iwate", "岩手県")
    miyagi = ("miyagi", "宮城県")
    akita = ("akita", "秋田県")
    yamagata = ("yamagata", "山形県")
    fukushima = ("fukushima", "福島県")
    ibaraki = ("ibaraki", "茨城県")
    tochigi = ("tochigi", "栃木県")
    gunma = ("gunma", "群馬県")
    saitama = ("saitama", "埼玉県")
    chiba = ("chiba", "千葉県")
    tokyo = ("tokyo", "東京都")
    kanagawa = ("kanagawa", "神奈川県")
    niigata = ("niigata", "新潟県")
    toyama = ("toyama", "富山県")
    ishikawa = ("ishikawa", "石川県")
    fukui = ("fukui", "福井県")
    yamanashi = ("yamanashi", "山梨県")
    nagano = ("nagano", "長野県")
    gifu = ("gifu", "岐阜県")
    shizuoka = ("shizuoka", "静岡県")
    aichi = ("aichi", "愛知県")
    mie = ("mie", "三重県")
    shiga = ("shiga", "滋賀県")
    kyoto = ("kyoto", "京都府")
    osaka = ("osaka", "大阪府")
    hyogo = ("hyogo", "兵庫県")
    nara = ("nara", "奈良県")
    wakayama = ("wakayama", "和歌山県")
    tottori = ("tottori", "鳥取県")
    shimane = ("shimane", "島根県")
    okayama = ("okayama", "岡山県")
    hiroshima = ("hiroshima", "広島県")
    yamaguchi = ("yamaguchi", "山口県")
    tokushima = ("tokushima", "徳島県")
    kagawa = ("kagawa", "香川県")
    ehime = ("ehime", "愛媛県")
    kochi = ("kochi", "高知県")
    fukuoka = ("fukuoka", "福岡県")
    saga = ("saga", "佐賀県")
    nagasaki = ("nagasaki", "長崎県")
    kumamoto = ("kumamoto", "熊本県")
    oita = ("oita", "大分県")
    miyazaki = ("miyazaki", "宮崎県")
    kagoshima = ("kagoshima", "鹿児島県")
    okinawa = ("okinawa", "沖縄県")
    kaigai = ("kaigai", "海外")


    def __init__(
        self, 
        pref_kana: str,
        pref: str
    ) -> None:
        self.pref_kana = pref_kana
        self.pref = pref

    @classmethod
    def get_yomi_by_name(cls, pref):
        for item in cls:
            if item.pref == pref:
                return item.pref_kana
        return None


class GetCompanyInfoEngage(GetCompanyInfoMixin):
    """
    エンゲージから企業情報を取得するクラス
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
                base_url="https://en-hyouban.com",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索用URLを作成
        self.SEARCH_PAGE_URL = f"{self.BASE_URL}/search/" + "area/{}/" + "industry/aitei-tsushin/"


    def _remove_extra_phrases(self, company_name: str) -> str:
        """
        会社名の付与されている無駄な文言を削除
        """
        return company_name


    def _create_company_name_list(
        self,
        url_: str,
        output_list: List[str] = []
    ) -> Tuple[List[str], str]:
        company_name_list = []
        # 企業詳細ページを展開
        driver = self.init_selenium_ff_get_page(url_=url_)
        company_name_list_elements = driver\
                .find_elements(By.CLASS_NAME, "company_name_anchor")

        # 余計な文言を取り除いた会社名でリストを作成
        for company_name_element in company_name_list_elements:
            company_name = self._remove_extra_phrases(
                company_name=company_name_element.text
            )
            if company_name not in output_list:
                # サイト内での会社名の被らない物のみリストに追加
                company_name_list.append(company_name)
        # 次にアクセスするページのURLを取得
        nextpage = self._get_next_page_url(url_=url_, driver=driver)
        return company_name_list, nextpage


    def _get_next_page_url(
        self,
        url_: str,
        driver: Union[ChromeWebDriver, FirefoxWebDriver]
    ) -> None:
        """
        次のページ用のURLを取得
        """
        nextpage = ""
        # 最終ページかチェック
        try:
            exist_next_page_element = driver.find_element(By.CSS_SELECTOR, 'a[rel="next"]')
            if exist_next_page_element:
                # 次のページが存在する場合、現在のページ数を取得
                current_page_element = driver.find_element(By.CLASS_NAME, "current-page")
                curry_page = current_page_element.text
                # ページより前方のURLを取得
                url_before_page = url_.split("?page")[0]
                # 次のページを生成
                nextpage = f"{url_before_page}?page={str(int(curry_page) + 1)}"
                print(f"next page url: {nextpage}")
            else:
                raise(Exception)
        except:
            print("Reached the last page.")
            nextpage = ""
    
        driver.close()
        return nextpage


    def execute(
        self,
        prefecture_list: List[str] = [],
        output_filename: str = "./temp.txt",
        output_flg: bool = False
    ) -> List[str]:
        """
        会社名リスト作成を実行
        """
        # Slack通知
        self.slack_client.post_message(
            source="エンゲージ",
            message="処理を開始します。"
        )
        output_company_list = []
        for prefecture in prefecture_list:
            # ページURL生成
            url_ = self.SEARCH_PAGE_URL.format(PrefectureType.get_yomi_by_name(pref=prefecture))
            try:
                # 検索ページトップ画面の一覧から会社名を取得
                c_name_list, next_url = self._create_company_name_list(
                            url_=url_, output_list=output_company_list)
                output_company_list.extend(c_name_list.copy())
                # 次のページURL取得
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
                    # 次のページURL取得
                    if not next_url:
                        # 次のページがない場合、ループ終了
                        break
            except Exception as e:
                import traceback
                # Slack通知
                self.slack_client.post_message(
                    source="エンゲージ",
                    message=traceback.format_exc(),
                    status="warn"
                )

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        # Slack通知
        self.slack_client.post_message(
            source="エンゲージ",
            message=f"媒体から会社名の取得が完了しました。 {len(output_company_list)} 件"
        )
        return output_company_list


if __name__ == "__main__":

    def str_to_list(arg):
        return arg.split(',')

    import argparse
    # 引数の設定
    parser = argparse.ArgumentParser(description='エンゲージから会社の情報を取得する')
    parser.add_argument("--interval", type=int, help="処理の間隔時間(秒)", default=2)
    parser.add_argument("--prefecture-list", type=str_to_list, help="媒体サイト内での都道府県名リスト", default=[])
    parser.add_argument("--output", type=bool, help="中間ファイル出力可否フラグ", default=True)
    parser.add_argument("--file_text", type=str, help="出力ファイル名(text).", default="./temp_engage.txt")
    parser.add_argument("--file_csv", type=str, help="出力ファイル名(csv/tsv).", default="./temp_dict_engage.csv")
    args = parser.parse_args()
    # 引数の取得
    interval = args.interval
    prefecture_list = args.prefecture_list
    output_flg = args.output
    output_filename_text = args.file_text
    output_filename_csv = args.file_csv

    if not prefecture_list:
        prefecture_list = [
            # "北海道",
            # "青森県",
            # "岩手県",
            # "宮城県",
            # "秋田県",
            # "山形県",
            # "福島県",
            # "茨城県",
            # "栃木県",
            # "群馬県",
            # "埼玉県",
            # "千葉県",
            "東京都",
            # "神奈川県",
            # "新潟県",
            # "富山県",
            # "石川県",
            # "福井県",
            # "山梨県",
            # "長野県",
            # "岐阜県",
            # "静岡県",
            # "愛知県",
            # "三重県",
            # "滋賀県",
            # "京都府",
            # "大阪府",
            # "兵庫県",
            # "奈良県",
            # "和歌山県",
            # "鳥取県",
            # "島根県",
            # "岡山県",
            # "広島県",
            # "山口県",
            # "徳島県",
            # "香川県",
            # "愛媛県",
            # "高知県",
            # "福岡県",
            # "佐賀県",
            # "長崎県",
            # "熊本県",
            # "大分県",
            # "宮崎県",
            # "鹿児島県",
            # "沖縄県",
            # "海外"
        ]

    company_list = []
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoEngage(interval=interval, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(prefecture_list=prefecture_list, output_filename=output_filename_text, output_flg=output_flg)
    get_company_info.create_company_info(company_name_list=company_list, source="エンゲージ", output_filename=output_filename_csv, output_flg=output_flg)
