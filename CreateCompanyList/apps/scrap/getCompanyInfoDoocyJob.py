# -*- coding: utf-8 -*-

import csv
import re
import time
import os
import sqlite3
import datetime
from typing import List, Dict, Union, Tuple

import cchardet
import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By

# 削除予定
import sys
sys.path.append('./')

from common.db.mariaDbManager import MariaDbManager


class GetCompanyInfoMixin:
    """
    各求人媒体より企業情報を取得する基底クラス
    """

    # サイト内文字コード
    CHAR_CODE = 'utf-8'
    # CHAR_CODE = 'SHIFT_JIS'
    # サーチエンジン検索用
    SERCH_ENGIN_URL = "https://www.google.com/search?q="
    # URLパターン
    URL_PTN = r"(https?://[\w/:%#\$&\?\(\)~\.=\+\-]+)(.*)"
    # ベースディレクトリ
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Selenium用Chromeドライバ格納ディレクトリ
    DRIVER_PATH = os.path.join(BASE_DIR, "driver")
    # SQL格納ディレクトリ
    SQL_DIR = os.path.join(BASE_DIR, "sql")
    # 接続するDB名
    # DB_NAME = "main.db"

    def __init__(self, base_url, interval, purge_domein_list=[], *args, **kwargs):
        # 媒体のベースURL
        self.BASE_URL = base_url
        # ページ取得の間隔(秒)
        self.INTERVAL_TIME = interval
        # 取り除く会社ドメインリスト
        self.PURGE_DOMEIN_LIST = purge_domein_list


    def init_selenium_get_page(self, url_):
        # ブラウザ非動作オプション
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        # ドライバ名
        driver_name = "chromedriver"
        if os.name == "nt":
            # Windowsの場合
            driver_name += ".exe"
        # ドライバセット
        driver = webdriver.Chrome(
                executable_path=os.path.join(
                        self.DRIVER_PATH, driver_name), options=options)
        # 検索
        driver.get(url_)
        return driver


    def init_selenium_ff_get_page(self, url_):
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1920, 2160)
        # 検索
        driver.get(url_)
        return driver


    def parse_html(self, url_):
        """
        htmlのパース
        """
        # インターバル
        time.sleep(self.INTERVAL_TIME)
        # 対象ページのHTMLの取得
        response = requests.get(url=url_)
        # 文字化け対策
        self.CHAR_CODE = cchardet.detect(response.content)["encoding"]
        # htmlのパース
        return bs(response.content, "lxml", from_encoding=self.CHAR_CODE)
    

    def _is_not_purge_url(self, company_url):
        """
        媒体等のURLかどうか判定(除かない場合True)
        """
        not_purge_flg = True
        for p_domein in self.PURGE_DOMEIN_LIST:
            # 対象URLが除くドメインリストに入っているか確認
            if p_domein in company_url:
                not_purge_flg = False
                break
        return not_purge_flg


    def create_company_info(self, conmpany_name_list, output_filename="./temp_dict_.csv", output_flg=False):
        company_info = []
        for company_name in conmpany_name_list:
            company_info.append(
                    self.get_company_url(conmapny_name=company_name).copy())
        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data_csv(filename_=output_filename,
                    data=company_info)

        return company_info


    def create_company_infos(self, conmpany_name_list, output_filename="./temp_dict_.csv", output_flg=False):
        company_info = []
        for company_name in conmpany_name_list:
            company_url = self.get_company_url(conmapny_name=company_name[0]).copy()
            company_info.append(
                dict(
                    **company_url,
                    **{"capital": company_name[1], "employees": company_name[2], "page": company_name[3]}
                )
            )
        if output_flg:
            # 外部ファイルへの書き出し
            self.output_datas_csv(filename_=output_filename,
                    data=company_info)
        # データ保存
        self.save(data_list=company_info)
        return company_info
    

    def get_company_url(self, conmapny_name):
        """
        会社名でググってURLを取得
        """
        # インターバル
        time.sleep(self.INTERVAL_TIME)
        # 会社HP検索用URL作成
        url_ = "{base_url}{name}%E3%80%80会社概要".format(
                        base_url=self.SERCH_ENGIN_URL, name=conmapny_name)
        # 検索結果一覧を取得
        # driver = self.init_selenium_get_page(url_=url_)
        driver = self.init_selenium_ff_get_page(url_=url_)
        company_url = ""
        # URLのリスト取得
        for i, elemh3 in  enumerate(driver.find_elements(By.XPATH, "//a/h3")):
            # 検索エンジンにてヒットしたサイト一覧
            matched_article = re.match(r"^.*会社(概要|案内|情報).*$", elemh3.text)
            _url = ""
            if matched_article or i == 0:
                # タイトルマッチする記事、もしくは検索した先頭に上がってきた記事
                elema = elemh3.find_element(By.XPATH, "..")
                # 企業URL
                _url = elema.get_attribute("href")
                if self._is_not_purge_url(company_url=_url):
                    # 企業サイトのURL
                    company_url = _url
                    break
            else:
                continue
        # ブラウザを閉じる
        driver.close()
        return {"name": conmapny_name, "url": company_url}


    def output_data(self, filename_, data_list):
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            for data in data_list:
                try:
                    fw.write(f"{data}\n")
                except UnicodeEncodeError:
                    ascii_data = data.encode("ascii", errors="ignore")
                    fw.write(f"{ascii_data}\n")


    def output_data_csv(self, filename_, data, delimiter='\t'):
        with open(filename_, mode="w", encoding=self.CHAR_CODE, newline="") as fw:
            write_csv = csv.writer(fw, delimiter=delimiter)
            for d in data:
                try:
                    write_csv.writerow([d["name"], d["url"]])
                except:
                    name = d["name"]
                    ascii_name = name.encode("ascii", errors="ignore")
                    write_csv.writerow([ascii_name, d["url"]])
                    continue


    def output_datas_csv(
        self,
        filename_: str,
        data: List[Dict[str, Union[str, int]]],
        delimiter: str ='\t'
    ) -> None:
        with open(filename_, mode="w", encoding=self.CHAR_CODE, newline="") as fw:
            write_csv = csv.writer(fw, delimiter=delimiter)
            for d in data:
                try:
                    write_csv.writerow([d["name"], d["url"], d["capital"], d["employees"]])
                except:
                    write_csv.writerow(["会社名エンコード失敗", d["url"]])
                    continue


    def save(self, data_list: List[Dict[str, Union[str, int]]]) -> None:
        # DBへデータを保存
        mdb_manager = MariaDbManager()
        # mariaDBのcursorを生成
        mdb_manager.generate_cursor()
        if not self.exists_table(mdb=mdb_manager):
            # テーブル作成
            self.create_table(mdb=mdb_manager)
        # データ挿入
        self.insert_company_info(mdb=mdb_manager, data_list=data_list)
        # BDの接続を解除
        mdb_manager.close()


    def _get_sql(self, filename: str) -> str:
        filepath = os.path.join(self.SQL_DIR, filename)
        with open(file=filepath, mode="r") as fsql:
            sql = fsql.read()
        return sql


    def exists_table(self, mdb: MariaDbManager) -> List[Union[Tuple[str], None]]:
        sql = self._get_sql(filename="exists_table.sql")
        print(sql)
        return mdb.execute(sql=sql)


    def create_table(self, mdb: MariaDbManager) -> None:
        sql = self._get_sql(filename="create_table_companys_info.sql")
        print(sql)
        mdb.execute(sql=sql)


    def insert_company_info(
        self,
        mdb: MariaDbManager,
        data_list: List[Dict[str, Union[str, int]]]
    ) -> None:
        base_sql = self._get_sql(filename="insert_company_info.sql")
        for d in data_list:
            c_name = d.get("name", "")
            c_url = d.get("url", "")
            c_capital = d.get("capital", "")
            c_employee = d.get("employees", "")
            c_page=d.get("page", 0)
            c_source=d.get("source", "")
            # 挿入用データ作成
            insert_data = "'{name}', '{url}', '{employees}', '{capital}', {page}, '{source}', NOW()".format(
                name=c_name,
                url=c_url,
                capital=c_capital,
                employees=c_employee,
                page=c_page,
                source=c_source,
            )
            # SQL生成
            sql = base_sql.format(
                insert_data=insert_data,
                company=c_name,
                url=c_url
            )
            print(sql)
            # insert実行
            mdb.execute(sql=sql)


class GetCompanyInfoDoocyJob(GetCompanyInfoMixin):
    """
    ドーシージョブから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = "(.+)(【|（)(.+)(】|）)"

    def __init__(self, interval=5, purge_domein_list=[], *args, **kwargs):
        super().__init__(
                base_url="https://doocy.jp",
                interval=interval, 
                purge_domein_list=purge_domein_list,
                *args,
                **kwargs
        )
        # 検索キーワード
        keyword = kwargs.get("keyword")
        if keyword:
            # 検索用URLを作成
            self.SEARCH_PAGE_URL = "{url}/jobs?&keyword={keyword}"\
                        .format(url=self.BASE_URL, keyword=keyword)
        else:
            # キーワードなしエラー
            pass


    def _create_company_name_list(self, url_, output_list):
        # 会社一覧ページをパース
        soup = self.parse_html(url_=url_)
        company_name_list = []
        for company_name in soup.find_all("p", class_="text-gray-56"):
            if company_name:
                # 会社名がnullではない
                conpany_name_text = company_name.text
                if conpany_name_text not in company_name_list \
                                and conpany_name_text not in output_list:
                    # 重複なし
                    company_name_list.append(conpany_name_text)
        return company_name_list


    def _get_next_page_url(self, url_):
        """
        次のページ用のURLを取得
        """
        soup = self.parse_html(url_=url_)
        # ページャURL全件取得
        p_links = soup.find_all("a", class_="page-link")
        nextpage = ""
        for link in p_links:
            if link.get("rel"):
                if "next" in link.get("rel"):
                    # 次ページのURLを取得
                    nextpage = link.get("href")
                    break

        if nextpage:
            # 基となるURLと次ページのURLを合わせる
            nextpage = "{base_url}{next}"\
                .format(base_url=self.BASE_URL, next=nextpage)
        return nextpage


    def execute(self, output_filename="./temp.txt", output_flg=False):
        """
        会社名リスト作成を実行
        """
        output_company_list = []
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

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data(filename_=output_filename,
                    data_list=output_company_list)
        return output_company_list


if __name__ == "__main__":
    company_list = []
    get_company_info = None

    # with open("rikunabi_next_temp.txt", mode="r", encoding="SHIFT_JIS") as f:
    #     company_list.extend(f.read().splitlines())
    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoDoocyJob(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(output_filename="./temp_doocyjob.txt", output_flg=True)
    get_company_info.create_company_info(conmpany_name_list=company_list, output_filename="./temp_dict_doocyjob.csv", output_flg=True)
