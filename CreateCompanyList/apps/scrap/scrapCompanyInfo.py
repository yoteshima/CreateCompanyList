# -*- coding: utf-8 -*-

import csv
import re
import time
import os

import cchardet
import requests
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By


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
    # Selenium用Chromeドライバ格納ディレクトリ
    DRIVER_PATH = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "driver")
    

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


    def create_company_info(self, conmpany_name_list, output_flg=False):
        company_info = []
        for company_name in conmpany_name_list:
            company_info.append(
                    self.get_company_url(conmapny_name=company_name).copy())
        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data_csv(filename_="./temp_dict_.csv",
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
                    fw.write("会社名エンコード失敗\n")
        

    def output_data_csv(self, filename_, data, delimiter='\t'):
        with open(filename_, mode="w", encoding=self.CHAR_CODE, newline="") as fw:
            write_csv = csv.writer(fw, delimiter=delimiter)
            for d in data:
                try:
                    write_csv.writerow([d["name"], d["url"]])
                except:
                    write_csv.writerow(["会社名エンコード失敗", d["url"]])
                    continue


class GetCompanyInfoType(GetCompanyInfoMixin):
    """
    @typeから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = "(.+)(【|（)(.+)(】|）)"


    def __init__(self, interval=5, purge_domein_list=[], *args, **kwargs):
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

    
    def _remove_other_company_name(self, company_name):
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


    def _create_company_name_list(self, url_, output_list):
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
                    # 重複なし
                    company_name_list.append(conpany_name_text)
        return company_name_list


    def _get_next_page_url(self, url_):
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
        return nextpage


    def execute(self, output_flg=False):
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
            self.output_data(filename_="./temp.txt",
                    data_list=output_company_list)
        return output_company_list


class GetCompanyInfoGreen(GetCompanyInfoMixin):
    """
    Greenから企業情報を取得するクラス
    """
    # 【】や()の文字列を検出するパターン
    PTN = "(.+)(【|（)(.+)(】|）)"


    def __init__(self, interval=5, purge_domein_list=[], *args, **kwargs):
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


    def _create_company_name_list(self, url_, output_list):
        # 会社一覧ページをパース
        soup = self.parse_html(url_=url_)
        company_name_list = []
        for company_name in soup.find_all("h3", class_="card-info__detail-area__box__title"):
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
        p_next = soup.find("a", class_="next_page")
        nextpage = ""
        if p_next:
            # 次のページのURLが存在する
            nextpage = p_next.get("href")
        if nextpage:
            # 基となるURLと次ページのURLを合わせる
            nextpage = "{base_url}{next}"\
                .format(base_url=self.BASE_URL, next=nextpage)
        return nextpage


    def execute(self, output_flg=False):
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
            self.output_data(filename_="./temp.txt",
                    data_list=output_company_list)
        return output_company_list


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


    def execute(self, output_flg=False):
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
            self.output_data(filename_="./temp.txt",
                    data_list=output_company_list)
        return output_company_list


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

    def __init__(self, interval=5, purge_domein_list=[], *args, **kwargs):
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


    def _cleansing_company_name(self, company_element):
        company_name = company_element.text
        matched = re.match(self.COMPANY_NAME_PTN, company_name)
        if matched:
            return matched.group(1)
        matched = re.match(self.KAKKO_PTN, company_name)
        if matched:
            return matched.group(3)
        return company_name


    def _get_pure_company_name(self, company_element):
        try:
            company_link_element = company_element.find_element(By.TAG_NAME, "a")
            c_link = company_link_element.get_attribute('href')
            soup = self.parse_html(url_=c_link)
            breadcrumb = soup.find("ul", class_="rnn-breadcrumb")
            return breadcrumb.text.splitlines()[-1]
        except:
            return company_element.text


    def _is_filtered_keyword(self, discripts):
        for discript in discripts:
            for key in self.KEYWOED:
                if key in discript.text:
                    return True
        return False


    def get_next_page_url(self, driver):
        try:
            next_page_element = driver.find_element(By.CLASS_NAME, "rnn-pagination__next")
            next_page_link_element = next_page_element.find_element(By.TAG_NAME, "a")
            return next_page_link_element.get_attribute('href')
        except Exception as e:
            print("最終ページです。")
            print(e)


    def _search_keyword(self, driver):
        # ページのキーワード検索する
        input_keyword_element = driver.find_element(By.CLASS_NAME, "rn3-conditionKeywordInput__input")
        input_keyword_element.send_keys(self.keyword)
        # 検索ボタンを押下
        search_button_element = driver.find_element(By.CLASS_NAME, "rn3-sideConditionalSearch__buttonSearch")
        search_button_element.click()

        return driver


    def _create_company_name_list(self, driver, output_list=[]):
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


    def execute(self, output_flg=False):
        """
        会社名リスト作成を実行
        """
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
            self.output_data(filename_="rikunabi_next_temp.txt",
                    data_list=output_company_list)
        return output_company_list


if __name__ == "__main__":
    import sys
    medium_type = sys.argv[1]

    company_list = []
    get_company_info = None

    with open("rikunabi_next_temp.txt", mode="r", encoding="SHIFT_JIS") as f:
        company_list.extend(f.read().splitlines())
    purge_domein_list = ['wantedly.com']

    if medium_type == 'type':
        get_company_info = GetCompanyInfoType(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
        company_list = get_company_info.execute(output_flg=True)
    elif medium_type == 'green':
        get_company_info = GetCompanyInfoGreen(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
        company_list = get_company_info.execute(output_flg=True)
    elif medium_type == 'doocy':
        get_company_info = GetCompanyInfoDoocyJob(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
        company_list = get_company_info.execute(output_flg=True)
    elif medium_type == 'rikunabi':
        get_company_info = GetCompanyInfoRikunabi(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
        company_list = get_company_info.execute(output_flg=True)
    else:
        raise(Exception)

    get_company_info.create_company_info(conmpany_name_list=company_list, output_flg=True)
