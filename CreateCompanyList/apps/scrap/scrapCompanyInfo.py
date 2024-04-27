# -*- coding: utf-8 -*-

import csv
import re
import time
import os
from typing import List, Dict, Union, Tuple

import cchardet
import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxWebDriver

# 削除予定
import sys
sys.path.append('./')

from common.db.mariaDbManager import MariaDbManager


class GetCompanyInfoMixin:
    """
    各求人媒体より企業情報を取得する基底クラス
    """

    # サイト内文字コード
    CHAR_CODE = 'SHIFT_JIS'
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

    def __init__(
        self,
        base_url: str,
        interval: int,
        purge_domein_list: List[str] = [],
        *args,
        **kwargs
    ) -> None:
        # 媒体のベースURL
        self.BASE_URL = base_url
        # ページ取得の間隔(秒)
        self.INTERVAL_TIME = interval
        # 取り除く会社ドメインリスト
        self.PURGE_DOMEIN_LIST = purge_domein_list


    def init_selenium_get_page(self, url_: str) -> ChromeWebDriver:
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


    def init_selenium_ff_get_page(self, url_: str) -> FirefoxWebDriver:
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        driver = webdriver.Firefox(options=options)
        driver.set_window_size(1920, 2160)
        # 検索
        driver.get(url_)
        return driver


    def parse_html(self, url_: str) -> bs:
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
    

    def _is_not_purge_url(self, company_url: str) -> bool:
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


    def create_company_info(
        self,
        company_name_list: List[str],
        source: str,
        output_filename: str = "./temp_dict_.csv",
        output_flg: bool = False
    ) -> List[str]:
        print(f"start process: add company url. Lists length total: {len(company_name_list)}")
        company_info = []
        for i, company_name in enumerate(company_name_list, start=1):
            print(f"in processing... {i}/{len(company_name_list)}", end="\r")
            company_url = self.get_company_url(conmapny_name=company_name).copy()
            company_info.append(
                dict(
                    **company_url,
                    **{"source": source}
                )
            )
        # データ保存
        self.save(data_list=company_info)

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data_csv(filename_=output_filename,
                    data=company_info)
        print("finish process: added company url.")
        return company_info


    def create_company_infos(
        self,
        company_name_list: List[List[str]],
        source: str,
        output_filename: str = "./temp_dict_.csv",
        output_flg: bool = False
    ) -> List[Dict[str, Union[str, int]]]:
        print(f"start process: add company url. Lists length total: {len(company_name_list)}")
        company_info = []
        for i, company_name in enumerate(company_name_list, start=1):
            print(f"in processing... {i}/{len(company_name_list)}", end="\r")
            company_url = self.get_company_url(conmapny_name=company_name[0]).copy()
            company_info.append(
                dict(
                    **company_url,
                    **{"capital": company_name[1], "employees": company_name[2], "page": company_name[3], "source": source}
                )
            )
        # データ保存
        self.save(data_list=company_info)

        if output_flg:
            # 外部ファイルへの書き出し
            self.output_datas_csv(filename_=output_filename,
                    data=company_info)
        print("finish process: added company url.")
        return company_info


    def get_company_url(self, conmapny_name: str) -> Dict[str, str]:
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
            # タイトルマッチする記事、もしくは検索した先頭に上がってきた記事
            elema = elemh3.find_element(By.XPATH, "..")
            # 企業URL
            _url = elema.get_attribute("href")
            if matched_article:
                if self._is_not_purge_url(company_url=_url):
                    # 企業サイトのURL
                    company_url = _url
                    break
            if i == 0:
                # 先頭に出てきたサイトのURLを保持
                company_url = _url
            else:
                continue
        # ブラウザを閉じる
        driver.close()
        return {"name": conmapny_name, "url": company_url}

        
    def output_data(self, filename_: str, data_list: List[str]) -> None:
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            for data in data_list:
                try:
                    fw.write(f"{data}\n")
                except UnicodeEncodeError:
                    fw.write("会社名のエンコードに失敗\n")


    def output_datas(
        self,
        filename_: str,
        data_list: List[List[Union[str, int]]]
    ) -> None:
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            for data in data_list:
                try:
                    fw.write(f"{data[0]}\n")
                except UnicodeEncodeError:
                    fw.write("会社名のエンコードに失敗\n")


    def output_data_csv(
        self,
        filename_: str,
        data: List[Dict[str, Union[str, int]]],
        delimiter: str = '\t'
    ) -> None:
        with open(filename_, mode="w", encoding=self.CHAR_CODE, newline="") as fw:
            write_csv = csv.writer(fw, delimiter=delimiter)
            for d in data:
                try:
                    write_csv.writerow([d["name"], d["url"]])
                except:
                    write_csv.writerow(["会社名のエンコードに失敗", d["url"]])
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


    def get_page(self, source: str) -> Union[int, None]:
        # DBへデータを保存
        mdb_manager = MariaDbManager()
        # mariaDBのcursorを生成
        mdb_manager.generate_cursor()
        # データ取得
        page = self.get_previous_page(mdb=mdb_manager)
        # BDの接続を解除
        mdb_manager.close()
        if page:
            return page[0][0]
        return None


    def _get_sql(self, filename: str) -> str:
        filepath = os.path.join(self.SQL_DIR, filename)
        with open(file=filepath, mode="r") as fsql:
            sql = fsql.read()
        return sql


    def get_previous_page(self, mdb: MariaDbManager) -> List[Union[Tuple[str], None]]:
        sql = self._get_sql(filename="get_latest_page.sql")
        print(sql)
        return mdb.execute(sql=sql)


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
            c_page=d.get("page", "")
            c_source=d.get("source", "")
            # 挿入用データ作成
            insert_data = "'{name}', '{url}', '{employees}', '{capital}', {page}, '{source}', NOW()".format(
                name=c_name,
                url=c_url,
                capital=c_capital,
                employees=c_employee,
                page=c_page if c_page else "NULL",
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
