# -*- coding: utf-8 -*-

import csv
import re
import time
import os
import random
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


    def create_company_infos(self, conmpany_name_list, source, output_filename="./temp_dict_.csv", output_flg=False):
        company_info = []
        for company_name in conmpany_name_list:
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
                    fw.write("会社名のエンコードに失敗\n")


    def output_datas(self, filename_, data_list):
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            for data in data_list:
                try:
                    fw.write(f"{data[0]}\n")
                except UnicodeEncodeError:
                    fw.write("会社名のエンコードに失敗\n")


    def output_data_csv(self, filename_, data, delimiter='\t'):
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


    def get_page(self) -> Union[int, None]:
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


class GetCompanyInfoFuma(GetCompanyInfoMixin):
    """
    FUMAから企業情報を取得するクラス
    """
    # 取得するページ数
    GET_PAGE_NUM = 10

    def __init__(self, to_page=0, interval=5, purge_domein_list=[], *args, **kwargs):
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
        # どのページからスタートするか
        self.TO_PAGE = to_page
        # どのページまで取得するか
        self.FROM_PAGE = to_page + self.GET_PAGE_NUM


    def generate_interval(self, min: int = 60, max: int = 300) -> int:
        return random.randint(min, max)


    def _get_company_details(self, url_):
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


    def _create_company_name_list(self, driver, output_list=[]):
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


    def execute(self, target_page=0, output_filename="./temp.txt", output_flg=False):
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
    company_list = []
    get_company_info = None

    purge_domein_list = ['wantedly.com']

    get_company_info = GetCompanyInfoFuma(keyword="情報サービス業", interval=2, purge_domein_list=purge_domein_list)
    company_list = get_company_info.execute(target_page=20, output_filename="./temp_fuma.txt", output_flg=True)
    get_company_info.create_company_infos(conmpany_name_list=company_list, source="Fuma", output_filename="./temp_dict_fuma.csv", output_flg=True)
