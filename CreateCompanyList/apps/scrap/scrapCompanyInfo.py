# -*- coding: utf-8 -*-

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
        """
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument(--no-sandbox")
        """
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
        driver = self.init_selenium_get_page(url_=url_)
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
        return {"name": conmapny_name, "url": company_url}

        
    def output_data(self, filename_, data_list):
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            fw.write("\n".join(data_list))
        

    def output_data_(self, filename_, data):
        with open(filename_, mode="a", encoding=self.CHAR_CODE) as fw:
            for d in data:
                fw.write("{}, {}\n".format(d["name"], d["url"]))


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
        company_name_list = company_name.split()
        # 会社名を取得
        c_name = company_name_list.pop(0)
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


    def create_company_info(self, conmpany_name_list, output_flg=False):
        company_info = []
        for company_name in conmpany_name_list:
            company_info.append(
                    self.get_company_url(conmapny_name=company_name).copy())
        if output_flg:
            # 外部ファイルへの書き出し
            self.output_data_(filename_="./temp_dict_.txt",
                    data=company_info)

        return company_info


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


if __name__ == "__main__":
    purge_domein_list = ['wantedly.com']
    get_company_info_type = GetCompanyInfoType(keyword="IT", interval=2, purge_domein_list=purge_domein_list)
    """
    company_list = get_company_info_type.execute(output_flg=True)
    """
    company_list = ["株式会社メイテック","株式会社ビッグモーター","Modis株式会社","GOMOAL株式会社","アイティアスリート株式会社","株式会社夢テクノロジー【東証プライム上場","セキュアエッジ株式会社","グローバルプレナーズ株式会社","株式会社アイ・エフ・ティ","株式会社ラーカイラム","株式会社ソフィアテック","株式会社プレアデスコンサルタント","abs株式会社","ジーエイチエス株式会社","AMBL株式会社","大国自動車交通株式会社","株式会社キュー・プレスト","株式会社HomeGrowin","株式会社アイテック","ジャパニアス株式会社","株式会社いえらぶパーク","株式会社Sunborn","Ｐｅｒｓｏｎ'ｓ株式会社","株式会社イズム","セントラル警備保障株式会社","ＳＯＭＰＯひまわり生命保険株式会社","株式会社ハイパーギア","セカンドサイトアナリティカ株式会社","株式会社ユーエスエス","株式会社KDDIエボルバ","株式会社アムク","株式会社ワイドテック","株式会社アルテニア","株式会社frenge","大東建託株式会社","オルターボ株式会社","ムーバクラウド株式会社","有限会社ケーズドットコム","のらねこワークス株式会社","株式会社アイ・ディ・エイチ","株式会社グローバー","株式会社エスラボ","株式会社リクルート","株式会社SEシェア","ジブラルタ生命保険株式会社","スイスポートジャパン株式会社","富士フイルムシステムサービス株式会社","株式会社ＩＴＳＯ","株式会社グリームオーブ","株式会社EMD","株式会社アンフォルム","株式会社要","株式会社アクロビジョン","株式会社ソフタスバリューコネクト","株式会社VISIONARY","フォイスHRプロサービス株式会社","株式会社ウィズテクノ","株式会社オービーシステム","株式会社セレマアシスト","セコム株式会社","山手交通株式会社","新幹線メンテナンス東海株式会社","日本交通埼玉株式会社","株式会社アールテクノ","日本交通株式会社","株式会社ガクエン住宅","株式会社マーキュリー","LivEdge株式会社","株式会社トゥインクル","株式会社ウェム","株式会社グッドワークコミュニケーションズ","イニシアティブソリューション株式会社","株式会社シティアスコムアイテック","オポチュニティーラボ株式会社","株式会社ココロザシ","HapInS株式会社","株式会社クルコム","株式会社ＲＥＶＯエンジニアリング","株式会社早稲田大学アカデミックソリューション","株式会社チョーサンテクノ","株式会社エー・アンド・ケー・コム","株式会社ＮｅｘｔＢｉｔｓ","株式会社システムフリージア","ジェイリース株式会社","株式会社ｅｆ","株式会社ＩＴＰＭ","株式会社大和・アクタス","株式会社イマジカアロベイス","株式会社アースインフィニティ","株式会社ネクステージ","オートグラス株式会社","株式会社ブランチ","株式会社ＡＴＪＣ","株式会社クロード","三松システムコンサルティング株式会社","株式会社プロシップ","株式会社エスアイイー","ビジョンズ株式会社","株式会社D-Standing","関東バス株式会社","UUUM株式会社","Ｈｉｔｚ環境サービス株式会社","株式会社システムアイ","株式会社テクノプロ","株式会社貴順","金森興業株式会社","株式会社レバレッジ","株式会社アイディーエス","株式会社レソリューション","株式会社無限の始まり","PCテクノロジー株式会社","FIC栄新株式会社","株式会社アイキューブ・マーケティング","株式会社クリエイティブスタイル","アイ・エイ・ジェイ株式会社","株式会社ヤマシンホーム","ラクラス株式会社","ニッカホーム関東株式会社","バーチャレクス・コンサルティング株式会社","株式会社","株式会社NODE","株式会社ワイエム交通","株式会社エンジョイ","株式会社Lcode","株式会社Ｒｏｏｍ１２","ＨＪホールディングス株式会社","Happy","ヤフー株式会社","羽田エアポートセキュリティー株式会社","株式会社ホッタ","株式会社ファンケル","株式会社ＳＯＮＯ","泉環境エンジニアリング株式会社","株式会社コンフィデンス","株式会社セイル","株式会社LainZ","株式会社NTTデータ","株式会社TheNewGate","株式会社トリドリ","メディアリンク株式会社","株式会社エンジーニアス","ソフィア総合研究所株式会社","Space","オムロン","株式会社シーエー・アドバンス","株式会社Struct","株式会社ユニバーサルソリューション総研","株式会社ネットサポート","株式会社Level","自興中販株式会社","株式会社ハイパーリンクソリューション","バルテス株式会社","シングルポイントジャパン合同会社","株式会社アルプスビジネスサービス","株式会社クリア","株式会社テクニケーション","アルファクラブ武蔵野株式会社","シミック・アッシュフィールド株式会社","株式会社ビルドイット","フクダライフテック東京株式会社","株式会社日本ワイドコミュニケーションズ","株式会社FUSIONIA","一般財団法人あんしん財団","株式会社アウトソーシングテクノロジー","株式会社メディア４ｕ","株式会社ＣＳＰクリエイティブサービス","楽天生命保険株式会社","株式会社イデアルアーキテクツ","株式会社ＮＫインターナショナル","株式会社キューブアンドカンパニー","株式会社ヴェシカ","ローグテクノロジーズ株式会社","ＴＢＫエアポートグランドサービス株式会社","株式会社ジャプロ","株式会社ケアライフワークス","ネイバーズ株式会社","株式会社システムエージェントジャパン","小林運輸株式会社","株式会社セノン","ハート株式会社","株式会社ホットランド","加藤ベニヤ株式会社","キリンメンテナンス・サービス株式会社","株式会社BSS","フルスタック株式会社","株式会社アジル・ラボ","ネクストフィールド株式会社","株式会社トレードワークス","株式会社エイム","株式会社リンクスタッフグループ","株式会社テックスレポート","株式会社テクノプラス","Y.W.C.株式会社","株式会社ウェーブ","株式会社リヴィティエ","株式会社全日警サービス神奈川","ファイブエージャパン株式会社","株式会社エグゼクティブプロテクション","株式会社デバンス","株式会社リードヴァンス","国立研究開発法人情報通信研究機構","株式会社ベクタス","株式会社ブリンクグループ","アクサス株式会社","株式会社エム・ソフト","ドリームジョイン株式会社","株式会社キアフィード","レッドロブスタージャパン株式会社","医療法人社団桜","ＴＡＣ株式会社","フクダ","株式会社フジワーク","株式会社ケーウェイズ","株式会社ユーテック","株式会社ウイングノア","株式会社マキバレ","合同会社TeCe","株式会社テックエデュケイションカンパニー","日東エレベータ株式会社","Marvel株式会社","ユニバーサル企業株式会社","株式会社日立インフォメーションエンジニアリング","株式会社システムズアプローチ","サンエイテレビ株式会社","株式会社relation","株式会社ゼネテック","平和自動車交通株式会社","株式会社メディカル電子工業","アクサ生命保険株式会社","ユニバース情報システム株式会社","株式会社ポポンデッタ","みんなのマーケット株式会社","アルムナイ株式会社","株式会社ソフトハート","株式会社ユーズテック","株式会社シーアイリンク","株式会社ベストリンク","株式会社キャリアイノベーション","株式会社バイク王＆カンパニー","株式会社ビジネスソフト","Tres","株式会社ｉ‐ＮＯＳ","株式会社コムレイド","株式会社ラグザス・クリエイト","株式会社末広システム","株式会社タカデン","株式会社ITreasure","株式会社村上組","株式会社ｂｌｕｅ","株式会社イデアル総研","関西デジタルソフト株式会社","ＱＬＣシステム株式会社","ＴＥＴＲＡＰＯＴ株式会社","株式会社ＭａｐｌｅＳｙｓｔｅｍｓ","株式会社ファイン","株式会社キャリアデザインセンター","株式会社アロン社","大樹生命保険株式会社","株式会社ピーアール・デイリー","日本コンセントリクス株式会社","株式会社エクステック","プロセスイノベーション株式会社","株式会社三ツ星","カイゼンベース株式会社","有限会社グリーンフラグ","株式会社大西","株式会社テクノクリエイティブ","株式会社オークレイ","株式会社EDIONクロスベンチャーズ","アポロ工業株式会社","株式会社読宣WEST","株式会社ワーキテクノ","株式会社パリエ","株式会社ワールドフェイマス","株式会社HNS","株式会社クラックスシステム","長谷川運輸倉庫株式会社","株式会社ＷｅＳｔｙｌｅ","滝興運株式会社","株式会社チェルト","株式会社High","株式会社利昭工業","ファイズオペレーションズ株式会社","有隣運送株式会社／青葉運輸株式会社","エヌ・ティ・ティ・システム開発株式会社","株式会社フラックス・エージェント","三菱電機システムサービス株式会社","アエラホーム株式会社","株式会社パーソンズ","株式会社アールツー","株式会社日本デジタル放送システムズ","セントラル技研株式会社","株式会社レオパレス21","株式会社ハツコーエレクトロニクス","ＳＥモバイル・アンド・オンライン株式会社","株式会社松村組","学校法人日本教育財団","株式会社オープンアップシステム","株式会社豊和ソフト","株式会社シムックスイニシアティブ","フラクタルシステムズ株式会社【ソフトウエア情報開発株式会社","資生堂インタラクティブビューティー株式会社","デジタルデータソリューション株式会社","医療法人社団上桜会","株式会社テレビ朝日メディアプレックス","伊藤忠マシンテクノス株式会社","株式会社インターネットイニシアティブ（IIJ）","パイオニア株式会社","TISシステムサービス株式会社","株式会社日本経済新聞社","株式会社アダストリア","CPAエクセレントパートナーズ株式会社","日本ＮＣＲ株式会社","株式会社ヒュープロ","株式会社BeeX","アベールソリューションズ株式会社","株式会社Dirbato","Apex株式会社","株式会社東洋新薬","みずほリサーチ&テクノロジーズ株式会社","株式会社Robot","株式会社サイバー・バズ","株式会社3CA","株式会社ワンスター","フリー株式会社","株式会社トップイノベーション","株式会社primeNumber","株式会社クランタス","SCSK株式会社","東京海上日動システムズ株式会社","株式会社カカクコム・インシュアランス","三菱総研ＤＣＳ株式会社","株式会社TVer","47内装株式会社","株式会社ロイヤリティ","株式会社バンダイナムコオンライン","伊藤忠インタラクティブ株式会社","ヤマト運輸株式会社","株式会社電通デジタル","アフラック生命保険株式会社","株式会社ベイカレント・コンサルティング","日野トレーディング株式会社","ソニービズネットワークス株式会社","株式会社ノーチラス・テクノロジーズ","コグニビジョン株式会社","キッセイコムテック株式会社","株式会社ベルチャイルド","サイネオス・ヘルス・コマーシャル株式会社","株式会社エーフォース","ＢＥＥＮＯＳ株式会社","株式会社ダイレクトソーシング","株式会社経営承継支援","楽天ペイメント株式会社","株式会社電通マクロミルインサイト","弁護士ドットコム株式会社","株式会社kotatsu","ハンズラボ株式会社","サンウエストホーム株式会社","株式会社ワールドインテック","東建コーポレーション株式会社","日本ソフテック株式会社","株式会社すき家","株式会社メイテックフィルダーズ","株式会社リクルートスタッフィング","株式会社テプコシステムズ","株式会社DAN","株式会社ＦＰパートナー","株式会社エムツーエム","株式会社ケアリッツ・テクノロジーズ","株式会社IDOM","株式会社アクセスネット","NRIシステムテクノ株式会社","株式会社Ｇｒｏｏｗ","ゲームプロダクション株式会社","株式会社テクノウェア","バリューアークコンサルティング株式会社","ICONIC","成田空港警備株式会社","フューチャーテクノロジー・コンサルティング株式会社","株式会社システム・クリエイト","フォーザウィン株式会社","株式会社ライジングサンセキュリティーサービス","株式会社オータム","株式会社ウィルオブ・ワーク","株式会社Ｃ－ｍｉｎｄ","株式会社エイトゲーム大陸","株式会社パイ・アール","株式会社ＳＣＲＩＰＴ","株式会社メディアドゥ","株式会社サウンドテクニカ","ストラクチュラルデザインストラテジー株式会社","株式会社ＫＵＮＯ","ラーニンギフト株式会社","株式会社イトーキ","株式会社ＮＳＤ","エイム株式会社","株式会社４ＤＩＮ","ウィードファウスト株式会社","株式会社ＪＣＤソリューション","ブックオフコーポレーション株式会社","ウイングソリューションズ株式会社","アデコ株式会社","株式会社宇徳ビジネスサポート","株式会社丸千代山岡家","株式会社日本テクノ開発","株式会社夢真","株式会社ジョーレン","グローバルコムサービス株式会社","FOX","共同エンジニアリング株式会社","パーソルプロセス＆テクノロジー株式会社","株式会社ハイレゾ","株式会社GainsLine","メットライフ生命保険株式会社","大同生命保険株式会社","株式会社ロジック","医療法人社団ＭＹメディカル","イオンクレジットサービス株式会社","株式会社さくらほりきり","株式会社HES","ノバシステム株式会社","新日本観光株式会社","アルタスソフトウェア株式会社","株式会社グミ","株式会社テクノプロ・コンストラクション","株式会社ティーネットジャパン","シモハナ物流株式会社","株式会社FEDELTA","株式会社A-urora","株式会社フリージア","株式会社月島ファクトリー","株式会社シーメイプル","株式会社ネオ・コーポレーション","ロジット株式会社","株式会社キカガク","キーエンスソフトウェア株式会社","株式会社エヌ・ティ・ティ・データ・セキスイシステムズ","千住金属工業株式会社","株式会社テクノクレア","バリューテクノロジー株式会社","株式会社シンサナミ","アイリスオーヤマ株式会社","アルテンジャパン株式会社","株式会社Ｔｉｍｏ","オブザーブ株式会社","NEXT株式会社（大阪支社・静岡支社)","株式会社ラクスパートナーズ","エムアイディ株式会社","株式会社ブレイン・ラボ","株式会社共立メンテナンス","ピンゴルフジャパン株式会社","株式会社フォトン算数クラブ","株式会社あかツキ","キヤノンビズアテンダ株式会社","フューチャー・スクウェア株式会社","株式会社ＯＮＥ","ビートテック株式会社","日本ＳＥ株式会社","Ｋ＆Ｋソリューション株式会社","株式会社アビリティ","株式会社エヌ・エイ・シー","株式会社Vエスティーエー","ＥＧテスティングサービス株式会社","株式会社SALTO","エクスウェア株式会社","辰巳電子工業株式会社","アイ・エフ・ディー株式会社","ＧＭＯコネクト株式会社【東証プライム上場","株式会社ワイズフューチャー","株式会社ザイナス","株式会社ブローウィッシュ","株式会社ウェルスペック","株式会社ティーケーピー","BaroqueWorks株式会社","株式会社Ｄｅｅｐｗｏｒｋ","エイブル保証株式会社","株式会社花咲ソリューション","アメージングアクティビティ株式会社","日本高圧洗浄株式会社","株式会社ジャストワーク","株式会社アジアピクチャーズエンタテインメント","株式会社クリエーション・ビュー","株式会社アイザワビルサービス","朝日ソーラー株式会社","株式会社トップエンジニアリング","一般社団法人アースエンジェルケアサポート","株式会社システムサポート","株式会社ホンダカーズ埼玉中","株式会社モバイルコミュニケーションズ","H.R.I","株式会社シンカ","東京ガスリックリビング株式会社","株式会社ティーオーエイチ","蔦交通株式会社","TDCフューテック株式会社","トライアロー株式会社","横浜トランスネット株式会社","株式会社ＹＯＫＵ","ハウンドジャパン株式会社","日本システムハウス株式会社","株式会社クロスパワー","インフィニアス株式会社","株式会社ライフコーポレーション","NEXT株式会社（虎ノ門本社)","ＲＩＺＡＰ株式会社","株式会社岩建ホームリニュ","株式会社ギア","株式会社エネサンス関東","株式会社ソシアス","株式会社ワイン・ラ・ターブル","株式会社oltre","東武ビジネスソリューション株式会社","新明電材株式会社","株式会社エスエルジャパン","株式会社サンマリエ","株式会社Branding","株式会社エンパワー","株式会社丸和運輸機関","株式会社TwinCompany","株式会社アイフリークモバイル","株式会社アイビーカンパニー","合同会社ナソリ","株式会社スマレジ","株式会社パック・エックス","株式会社ナミト","株式会社サイゼント","株式会社ＴＭＪ","インターリンク株式会社","株式会社タイムリー","株式会社ＥＣＨ","トランスコスモスパートナーズ株式会社","住友林業情報システム株式会社","株式会社キューネット","株式会社スカラコミュニケーションズ","イエローテイルズ株式会社","株式会社分析屋","株式会社Phoenixテクノロジーズ","ゼンプロジェクト株式会社","株式会社コインパーク","株式会社プログレス","株式会社ステップ","ホーチキ株式会社","株式会社マネジメントソリューションズ","株式会社アシスト","株式会社トライトキャリア","株式会社LOHASTYLE","株式会社NetFile","西華デジタルイメージ株式会社","三井不動産株式会社","株式会社ＵＲコミュニティ","小田急交通株式会社","株式会社神戸製鋼所","株式会社ジラフ","アリババ株式会社","サイボウズ株式会社","株式会社リクルートR&Dスタッフィング","株式会社ジョブズコンストラクション","株式会社スリーエス","京セラ株式会社","アビームコンサルティング株式会社","株式会社ＥＳＥＳ","株式会社イージスワン","株式会社TBM","株式会社Crane&I","株式会社カカクコム","株式会社物語コーポレーション","株式会社Dexall","株式会社第一コンピュータサービス","株式会社ウガトリア","オムロン株式会社","株式会社ＦＹＦ","株式会社セレクティ","日本道路興運株式会社","株式会社オンテックス","京葉コンピューターサービス株式会社","株式会社センス","Ｉｎｎｏｖａｔｉｏｎ","ラピードアクト株式会社","株式会社シーディア","株式会社ＮＥＣＴ","株式会社綜合キャリアオプション","株式会社ジェイエイシーリクルートメント","協和警備保障株式会社","フリーランスエージェント株式会社","エスケー住宅サービス株式会社","富士フイルムビジネスイノベーション株式会社","神奈中タクシー株式会社","株式会社サイバーエージェント","株式会社カラビナ","PwCコンサルティング合同会社","株式会社データサポート","株式会社エコリング","株式会社カメガヤ","日建リース工業株式会社","さくら情報システム株式会社","株式会社アクロス・シティ","アルファテクノロジー株式会社","株式会社イシカワコーポレーション","株式会社コロナワークス","株式会社サイコー","株式会社エイトエンジニアリング","日本マルコ株式会社","株式会社フレクト","株式会社ウェディングボックス","株式会社SPEED","楽天グループ株式会社","株式会社ベネッセコーポレーション","株式会社ワールドコーポレーション","ＡＬＳＯＫ東京株式会社【綜合警備保障（株）ALSOK","医療法人社団同友会","エイベックス株式会社","ワン・アンド・カンパニー株式会社","株式会社グッドワークス","株式会社ファインプラン","日の丸交通株式会社","日本交通横浜株式会社","株式会社NRC","ActCom株式会社","東洋交通株式会社","アクセラレイテッド・ソフトウェア・エンジニアリング合同会社","株式会社アセットホーム","株式会社ユームス","株式会社伊東園ホテルズ","全国農業協同組合連合会","株式会社とんでんホールディングス","ソフトバンク株式会社","株式会社ボルテックス","株式会社サンウェル【Sanwell,","株式会社静岡銀行","株式会社シルバーバックス・プリンシパル","株式会社デンソー","株式会社インフィライズ","株式会社アルゴビジネスサービス","日本ＰＭＣ株式会社","株式会社ガイアコミュニケーションズ","バジンガ株式会社","株式会社AGAIN","シュッピン株式会社","ウォータースタンド株式会社","株式会社ＩＴコミュニケーションズ","株式会社ねぎしフードサービス","株式会社プラウディア","日本ウェブサービス株式会社","株式会社ココナラ","Ｓｋｙ株式会社","株式会社サン・マルタカ","日産自動車株式会社","オリックス自動車株式会社","株式会社ミアーズ","株式会社いえらぶパートナーズ","東京福山通運グループ【合同募集】","エムディーアイ株式会社","株式会社Ｃａｎｖａｓ","株式会社ｆｒｅｅ","イズミ物流株式会社","東レ株式会社","株式会社三菱UFJ銀行","株式会社リーディング・エッジ社","株式会社玉","アヴァント株式会社","Ｓａｚｅ株式会社","シームレスサービス株式会社","株式会社アドバンスクリエイティブ/株式会社アドバンスワークス","株式会社エムケイエス","株式会社日本ビジネスデータープロセシングセンター","株式会社シンプルウェイ","豊玉タクシー株式会社","株式会社キーワードジャパン","GMOソリューションパートナー株式会社","株式会社エターナルサイエンス","アラコム株式会社","株式会社モトーレンティーアイ","株式会社TKK","株式会社ジェイテック","セレックバイオテック株式会社","パルシステムグループ","株式会社Liberta","首都高トールサービス神奈川株式会社","株式会社ＷＥＤＧＥ","トヨタ自動車株式会社","株式会社ＮＥＸＴ","株式会社フラット","株式会社Ｙ－Ｓ４","ＡＳＫＵＬ","ユニ・チャーム株式会社","株式会社ユニゾン・テクノロジー","株式会社LIFULL","株式会社ディー・エヌ・エー","株式会社Lecc","Ｔｅｃｈｎｏｃｒａｔｓ","テックコイン株式会社","株式会社エス・エム・エス","株式会社リッチ","株式会社ディーワン","アラクサラネットワークス株式会社","株式会社ベリアント","株式会社アップリンク","株式会社アクアードコンサルティング","株式会社ネットタッチソフトウェア","株式会社オズクリエイション","株式会社テックプロ","株式会社日立社会情報サービス","太平ビルサービス株式会社","株式会社スカイネット","株式会社Ｏｎｅ","株式会社ケイアイ","株式会社ブレイブテクノロジー","株式会社エーアイスミス","株式会社ベクトロジー","株式会社C","Xerotta株式会社","株式会社日立ソリューションズ","未来開発株式会社","都築工業","アクセス株式会社","株式会社ティー・アンド・ユー","株式会社日立システムズパワーサービス","株式会社マルコム","株式会社多摩流通","セルプロモート株式会社","株式会社カフェレオホールディングス","システムエンハンス合同会社","株式会社日立システムズ","株式会社レインオンファニー","株式会社シフォン","フェアシステム株式会社","日清食品グループ(日清食品株式会社)","株式会社わだち大泉","株式会社純アシスト","有限会社サクセスフュージョン","株式会社アクトエンジニアリング","ヤマトシステム開発株式会社","有限会社プリントメイト","株式会社ビーテックインターナショナル","ルネサス","株式会社ＳＥＴ","株式会社アイセルネットワークス","株式会社ＡＣＴ","BPOテクノロジー株式会社","株式会社池田山エステート","株式会社福井銀行","株式会社ライフスクエア","ユニテックシステム株式会社","株式会社丸井グループ","株式会社世田谷自動車学校","株式会社AirEraテクノロジー","株式会社Bug.s","横浜無線タクシーグループ","株式会社DHI","株式会社VOLLMONTホールディングス","株式会社キャップインフォ","株式会社ＪＲ東日本情報システム","株式会社アルスキューブ","株式会社日立アカデミー","株式会社トラストシステムソリューションズ","株式会社Ｄｏｏｒｓ","株式会社ウィモーション","株式会社ＡＮＯＴＨＥＲ","司法書士法人こがわ法務事務所","株式会社太陽ビルマネージメント","住友生命保険相互会社","ｅＧＩＳ株式会社","株式会社エヌ・エス・アール","渡辺興業株式会社","株式会社富士テクノソリューションズ","株式会社ヒューメインシステム","株式会社ユニオンシンク","株式会社京福商店","株式会社ハートソフト","株式会社ステージア","フコク物産株式会社","株式会社ウイングプラス","株式会社ＳｅｅＤ","株式会社トミーズコーポレーション","中央システムサービス株式会社","株式会社Redo","株式会社ジャパンプランニング","株式会社神戸クルーザー","株式会社ZELXUS","サン・エム・システム株式会社","東日本NSソリューションズ株式会社","株式会社ソルネットシステム","株式会社中谷本舗","日本パワーファスニング株式会社","ペタビット株式会社","株式会社グラブハーツ【CoCo壱番屋","株式会社Ｎａｓｃｏｍ","株式会社PONTE","株式会社Ｆｉｒｓｔ","株式会社ベルクリック","株式会社Green&Digital","株式会社ネオキャリア","CREFIL株式会社","株式会社アイティーシー","有限会社藤管工業","株式会社ケイプラン","株式会社ｄａｂ","ＪＨＲ株式会社","株式会社Japan","株式会社エフ・エフ・エル","UT東芝株式会社","和光電気工事株式会社","株式会社ファーストコンテック","株式会社キャリアデザインセンターtype就活エージェント部","株式会社コンタクト","株式会社イエスリフォーム","株式会社神戸物産","株式会社WASABI","オンライントラベル株式会社","株式会社グランド・ガーデン","ノヅック株式会社","株式会社ユキオー","株式会社ＴＯＹＯＤＡＴＡ","株式会社スクラムソフトウェア","ＳＫｅｒ株式会社","株式会社エヌエム・ヒューマテック","インフォシー株式会社","株式会社ホワイトホース","社会医療法人彩樹","株式会社ライズ","株式会社Y","株式会社イズミシステム設計","株式会社サワショウ","株式会社BEELEAF","リダクション株式会社","株式会社日本ハウスホールディングス","株式会社アジャイルウェア","日本エンジニアリングソリューションズ株式会社（略称：NES)","株式会社ジェムキャッスルゆきざき","株式会社オレンジ社","FutureRays株式会社","株式会社アサーティブ","株式会社Ｂｌａｎｃ","株式会社アンラベル","アマノ株式会社","ＭＳＰＣ株式会社","パーソルクロステクノロジー株式会社","アイデアパッケージ株式会社","株式会社ストーム","アジア株式会社","株式会社ＬＢＢ","株式会社ウェットウェア","株式会社ジェイロック","株式会社AGEST","株式会社エムズワークス","タカラスタンダード株式会社","株式会社日商","日交練馬株式会社","株式会社アイドマ・ホールディングス","株式会社アンビシャスグループ","日油株式会社","生和不動産保証株式会社","ミート物流株式会社","株式会社フルタイムシステム","株式会社御剣商事","小川電機株式会社","ワールドトランスシステム株式会社","株式会社エービーシステム","三楽建設株式会社","株式会社ビジネスブレーン","三和ペイント株式会社","川面ビルサービス株式会社","協栄企画システム株式会社","株式会社HIPUS","株式会社カヤックボンド","株式会社BeForward","三研メディアプロダクト株式会社","株式会社マジックウェイ","株式会社一家ダイニングプロジェクト","株式会社サンクプローブ","株式会社インタースペース","株式会社ＣＡＲＥＳソリューションセンター","株式会社ペンタイン","アイレット株式会社","システム・アナライズ株式会社","横須賀ソフトウェア株式会社","株式会社PRO技術","株式会社メガジェンジャパン","リンテック株式会社","株式会社オプティマ","学校法人電子学園","株式会社MTG","弥生株式会社","リーシング・マネジメント・コンサルティング株式会社","株式会社ブレインパッド","メディケア生命保険株式会社","サブライムコンサルティング株式会社","マンパワーグループ株式会社","株式会社PR","株式会社Algoage","株式会社フィックスターズ","マーサージャパン株式会社","富士フイルム株式会社","ガンホー・オンライン・エンターテイメント株式会社","綜合警備保障株式会社","株式会社ＫＡＤＯＫＡＷＡ","株式会社博報堂アイ・スタジオ","富士通株式会社","株式会社メディカルリソース","株式会社アールエンジン","株式会社アビスト","株式会社Geekly","株式会社MonotaRO","株式会社ビザスク","株式会社ＣＯＭＰＡＳＳ","クラシス株式会社","イオンスマートテクノロジー株式会社","株式会社システムエグゼ","NTTデータルウィーブ株式会社","プロパティデータバンク株式会社","CTCテクノロジー株式会社","STORES株式会社","株式会社東日本技術研究所","株式会社ビジョン・コンサルティング","浦安施設管理協同組合","住友化学株式会社","ジュピターショップチャンネル株式会社","株式会社GSI","株式会社スマイル","株式会社レップワン","ソニーペイメントサービス株式会社","パイプドHD株式会社","株式会社Ｈｅｌｐｆｅｅｌ","デジタルアーツ株式会社","株式会社インダストリー・ワン","株式会社ジールコミュニケーションズ","インテグループ株式会社","西日本電信電話株式会社","株式会社ウィルゲート","エヌ・ティ・ティ・コムウェア株式会社","株式会社日本総合研究所","株式会社wild","株式会社ＮＴＴデータビジネスシステムズ","ウルシステムズ株式会社","株式会社グラスト","株式会社シー・ビー・ティ・ソリューションズ","株式会社アドウェイズ","テクマトリックス株式会社","株式会社グロービス","株式会社良品計画","パーソルテクノロジースタッフ株式会社","インヴェンティット株式会社","ソニーグローバルマニュファクチャリング＆オペレーションズ株式会社","株式会社富士通エフサス","ＧＭＯフィナンシャルゲート株式会社","ソニーワイヤレスコミュニケーションズ株式会社","株式会社Amazia","株式会社スカイウイル","株式会社ナガセ","ビーパートナーズ株式会社","株式会社リターンハート","株式会社リツビ","ユージーメンテナンス株式会社","キャップジェミニ株式会社","株式会社CyberACE","EYストラテジー・アンド・コンサルティング株式会社","楽天スーパーロジスティクス株式会社","KDDI株式会社","富士フイルムビジネスイノベーションジャパン株式会社","株式会社ＡＢＥＪＡ","株式会社アド・プロ","ミネベアミツミ株式会社","株式会社クラレ","株式会社MS-Japan","株式会社バイトレ","ヨネックス株式会社","株式会社ＫＹＯＳＯ","川崎ライフケアクリニック","株式会社ＢＩＴＺ","株式会社LITALICO","PwCあらた有限責任監査法人","株式会社ユニラボ","イーテック株式会社","株式会社パソナＪＯＢ","株式会社VRAIN","株式会社Ｍ＆Ａ総合研究所","株式会社スタンバイ","テクノブレイブ株式会社","株式会社ラクス","株式会社アルプス技研","太陽グラントソントン・アドバイザーズ株式会社","株式会社菱友システムズ","株式会社インテグリティ・ヘルスケア","アドビ株式会社","株式会社テンポイノベーション","NTTコム","エムシーデジタル株式会社","三菱地所","HENNGE株式会社","キリンビジネスシステム株式会社","株式会社ニコン","株式会社レゾナック・ホールディングス","株式会社アクセライト","レバレジーズ株式会社","INTLOOP株式会社","株式会社三菱UFJ銀行（システム本部）","株式会社アイレップ","デロイト","株式会社キャリアデザインセンターtype転職エージェント事業部[ポジションマッチ登録]","ｄｅｌｙ株式会社","朝日インタラクティブ株式会社","株式会社カプコン","株式会社クルイト","47株式会社","SAPジャパン株式会社","ライフネット生命保険株式会社","ソニーネットワークコミュニケーションズ株式会社","SOMPOシステムズ株式会社","ＥＹストラテジー・アンド・コンサルティング株式会社","株式会社日本Ｍ＆Ａセンター","株式会社野村総合研究所","株式会社リクルート＜SUUMO領域＞","株式会社イングリウッド","Sansan株式会社","大正製薬株式会社","キヤノン電子テクノロジー株式会社","株式会社セキュアソフト","株式会社マネーパートナーズソリューションズ","アサヒクオリティーアンドイノベーションズ株式会社","エムスリーキャリア株式会社／開発部門","株式会社DeepX","日清食品株式会社","株式会社ツリーベル","株式会社ＫＭＣ","株式会社はてな","株式会社アクティブ・ワーク株式会社DAN","株式会社スタッフサービス","株式会社IDOM","株式会社Sunborn","株式会社キュー・プレスト","ジャパニアス株式会社","グローバルプレナーズ株式会社","Ｐｅｒｓｏｎ'ｓ株式会社","株式会社テクノウェア","株式会社プレアデスコンサルタント","AMBL株式会社","株式会社エイトゲーム大陸","株式会社いえらぶパーク","株式会社アイ・エフ・ティ","ストラクチュラルデザインストラテジー株式会社","大国自動車交通株式会社","株式会社アウトソーシングテクノロジー","株式会社４ＤＩＮ","ＳＯＭＰＯひまわり生命保険株式会社","株式会社イトーキ","株式会社ＮＳＤ","ムーバクラウド株式会社","のらねこワークス株式会社","株式会社KDDIエボルバ","NAYUTA株式会社","大東建託株式会社","オルターボ株式会社","株式会社テクノプロ","株式会社ユーエスエス","株式会社アルテニア","株式会社コプロ・エンジニアード","FOX","株式会社ＩＴＳＯ","スイスポートジャパン株式会社","株式会社ハイレゾ","株式会社エスラボ","株式会社ブランチ","株式会社ソフタスバリューコネクト","株式会社ティーネットジャパン","オートグラス株式会社","ノバシステム株式会社","アイ・エフ・ディー株式会社","株式会社マーキュリー","株式会社ウェルスペック","株式会社モバイルコミュニケーションズ","エイブル保証株式会社","アイリスオーヤマ株式会社","株式会社ＮｅｘｔＢｉｔｓ","株式会社クロード","セコム株式会社","株式会社共立メンテナンス","株式会社ロジック","オポチュニティーラボ株式会社","株式会社アビリティ","ビートテック株式会社","東武ビジネスソリューション株式会社","ＥＧテスティングサービス株式会社","株式会社ギア","株式会社分析屋","株式会社フリージア","株式会社ＹＯＫＵ","株式会社クルコム","株式会社テクノプロ・コンストラクション","株式会社ティーオーエイチ","株式会社","株式会社パック・エックス","株式会社プロシップ","株式会社Ｄｅｅｐｗｏｒｋ","株式会社アースインフィニティ","グローディア株式会社","株式会社エー・アンド・ケー・コム","株式会社グミ","株式会社綜合キャリアオプション","ピンゴルフジャパン株式会社","株式会社タイムリー","株式会社ｅｆ","株式会社エヌ・ティ・ティ・データ・セキスイシステムズ","ＧＭＯコネクト株式会社【東証プライム上場","株式会社岩建ホームリニュ","株式会社月島ファクトリー","株式会社アールテクノ","株式会社エンパワー","株式会社ＡＴＪＣ","一般社団法人アースエンジェルケアサポート","トランスコスモスパートナーズ株式会社","日本交通株式会社","HapInS株式会社","株式会社ガクエン住宅","株式会社ＯＮＥ","新幹線メンテナンス東海株式会社","株式会社スマレジ","株式会社Vエスティーエー","株式会社ウィズテクノ","株式会社ホッタ","株式会社アセットホーム","株式会社NetFile","株式会社デンソー","エムディーアイ株式会社","株式会社Struct","大樹生命保険株式会社","株式会社ＣＳＰクリエイティブサービス","株式会社アルス・ウェアー","Space","株式会社エンジーニアス","株式会社ユニバーサルソリューション総研","自興中販株式会社","ビジョンズ株式会社","株式会社テクニケーション","株式会社ネットサポート","ソフトバンク株式会社","アルファテクノロジー株式会社","株式会社ＮＥＸＴ","株式会社イデアルアーキテクツ","株式会社伊東園ホテルズ","株式会社ファンケル","エスケー住宅サービス株式会社","株式会社物語コーポレーション","株式会社エンジョイ","株式会社コロナワークス","株式会社ラストデータ","C-HRC株式会社","株式会社Lcode","株式会社コンフィデンス","ウォータースタンド株式会社","PCテクノロジー株式会社","株式会社ウガトリア","株式会社ＥＳＥＳ","株式会社ＦＹＦ","楽天グループ株式会社","Ｉｎｎｏｖａｔｉｏｎ","株式会社ファインプラン","株式会社アイキューブ・マーケティング","バーチャレクス・コンサルティング株式会社","東建コーポレーション株式会社","株式会社アルプスビジネスサービス","アビームコンサルティング株式会社","株式会社貴順","シュッピン株式会社","株式会社ジェイエイシーリクルートメント","UUUM株式会社","さくら情報システム株式会社","株式会社isub","富士フイルムビジネスイノベーション株式会社","株式会社ワイエム交通","株式会社Ｃａｎｖａｓ","株式会社グッドワークス","株式会社ｆｒｅｅ","首都高トールサービス神奈川株式会社","ドコモ・データコム株式会社","株式会社FUSIONIA","株式会社カメガヤ","株式会社エターナルサイエンス","株式会社Precious","株式会社とんでんホールディングス","ラクラス株式会社","フクダライフテック東京株式会社","株式会社U’ｓFactory","一般財団法人あんしん財団","株式会社NODE","アルファクラブ武蔵野株式会社","シングルポイントジャパン合同会社","株式会社エコリング","株式会社メック","株式会社VISIONARY","株式会社日本システムソリューション","株式会社ベネッセコーポレーション","株式会社トリドリ","アイ・エイ・ジェイ株式会社","パルシステムグループ","エイベックス株式会社","ＡＬＳＯＫ東京株式会社【綜合警備保障（株）ALSOK","日本ウェブサービス株式会社","株式会社メディア４ｕ","株式会社シルバーバックス・プリンシパル","株式会社ビルドイット","株式会社ＳＯＮＯ","株式会社イージスワン","泉環境エンジニアリング株式会社","株式会社日本ワイドコミュニケーションズ","株式会社ハイパーリンクソリューション","株式会社ハーマンドット","株式会社TKK","セルプロモート株式会社","株式会社アジル・ラボ","株式会社ホットランド","株式会社セノン","Y.W.C.株式会社","アルコ電機株式会社","株式会社ＮＫインターナショナル","ローグテクノロジーズ株式会社","株式会社ジャプロ","株式会社ベクタス","フェアシステム株式会社","国立研究開発法人情報通信研究機構","株式会社リヴィティエ","ファイブエージャパン株式会社","株式会社ＳＥＴ","株式会社フジワーク","株式会社ファーストピック","ユニテックシステム株式会社","アクサス株式会社","ヤマトシステム開発株式会社","株式会社ブリンクグループ","株式会社エグゼクティブプロテクション","ユニバーサル企業株式会社","合同会社TeCe","株式会社ゼネテック","サンエイテレビ株式会社","SMHC株式会社","株式会社トラストシステムソリューションズ","株式会社コアズ","株式会社メディカル電子工業","レッドロブスタージャパン株式会社","アクセス株式会社","株式会社AirEraテクノロジー","株式会社アクアードコンサルティング","医療法人社団桜","株式会社ケーウェイズ","株式会社ＪＲ東日本情報システム","株式会社relation","株式会社ステージア","ユニバース情報システム株式会社","株式会社コムレイド","株式会社ユニオンシンク","アクサ生命保険株式会社","司法書士法人こがわ法務事務所","株式会社ユーズテック","ｅＧＩＳ株式会社","アルムナイ株式会社","関西デジタルソフト株式会社","株式会社ソルネットシステム","株式会社ジャパンプランニング","株式会社富士テクノソリューションズ","渡辺興業株式会社","中央システムサービス株式会社","株式会社タカデン","株式会社エヌ・エス・アール","株式会社ウイングプラス","アポロ工業株式会社","株式会社シーアイリンク","日本パワーファスニング株式会社","株式会社Redo","エイチアールディー株式会社","株式会社アサーティブ","ケイアイエヌ株式会社","株式会社ジェムキャッスルゆきざき","株式会社アイドマ・ホールディングス","株式会社キャリアデザインセンター","株式会社ＬＢＢ","東京コンピュータシステム株式会社","株式会社ジェイテック","株式会社ワールドフェイマス","株式会社High","株式会社ネオキャリア","株式会社ピーアール・デイリー","インフォシー株式会社","株式会社Y","株式会社EDIONクロスベンチャーズ","株式会社アンラベル","Heyday株式会社","有限会社グリーンフラグ","ミート物流株式会社","株式会社アール・エム","株式会社クラックスシステム","FutureRays株式会社","株式会社Green&Digital","株式会社御剣商事","ファイズオペレーションズ株式会社","ｗｅｐａｒｋ株式会社","日交練馬株式会社","株式会社パーソンズ","株式会社Ｆｉｒｓｔ","株式会社ＭａｐｌｅＳｙｓｔｅｍｓ","株式会社アロン社","三和ペイント株式会社","株式会社大七住建","興和アシスト株式会社","みんなのマーケット株式会社","株式会社エムズワークス","株式会社ライズ","株式会社フラックス・エージェント","株式会社アンビシャスグループ","滝興運株式会社","アイデアパッケージ株式会社","株式会社三ツ星","株式会社GMW","株式会社パリエ","株式会社エクステック","株式会社サンクプローブ","株式会社オプティマ","株式会社カヤックボンド","横須賀ソフトウェア株式会社","学校法人電子学園","株式会社一家ダイニングプロジェクト","株式会社メガジェンジャパン","株式会社HIPUS","リンテック株式会社","株式会社インタースペース","ビーパートナーズ株式会社","松井建設株式会社","株式会社キャリアインデックス","アフラック生命保険株式会社","ハンズラボ株式会社","株式会社ベルチャイルド","資生堂インタラクティブビューティー株式会社","株式会社エーフォース","弁護士ドットコム株式会社","株式会社電通デジタル","株式会社NTTデータ","株式会社アドウェイズ","株式会社カプコン","ＢＥＥＮＯＳ株式会社","株式会社GSI","株式会社ＣＯＭＰＡＳＳ","ソニーグローバルマニュファクチャリング＆オペレーションズ株式会社","株式会社サイバー・バズ","リーシング・マネジメント・コンサルティング株式会社","株式会社LITALICO","楽天ペイメント株式会社","エムシーデジタル株式会社","伊藤忠マシンテクノス株式会社","株式会社テレビ朝日メディアプレックス","株式会社ヒュープロ","川崎ライフケアクリニック","株式会社ツカダ・グローバルホールディング","株式会社クラレ","ｄｅｌｙ株式会社","株式会社PR","株式会社ビザスク","株式会社ストリームライン","アベールソリューションズ株式会社","ライフネット生命保険株式会社","株式会社電通マクロミルインサイト","日野トレーディング株式会社","株式会社キャピタル・アセット・プランニング","パイプドHD株式会社","株式会社シオン","株式会社三菱UFJ銀行（システム本部）","コグニビジョン株式会社","株式会社MTG","マンパワーグループ株式会社","株式会社アールエンジン","株式会社ロイヤリティ","株式会社ニコン","株式会社日立医薬情報ソリューションズ","株式会社Geekly","株式会社ワンスター","株式会社メディカルリソース","株式会社グロービス","ＧＭＯフィナンシャルゲート株式会社","レバレジーズ株式会社","Sansan株式会社","クラシス株式会社","株式会社レップワン","ミイダス株式会社","株式会社ダイレクトソーシング","株式会社アルテニカ","ヤマト運輸株式会社","株式会社アクティブ・ワーク","株式会社ＫＭＣ","株式会社富士通エフサス","NTTデータルウィーブ株式会社","富士フイルム株式会社","エムスリーキャリア株式会社","Apex株式会社","富士通株式会社","日清食品株式会社","インテグループ株式会社","メディケア生命保険株式会社","アイティアスリート株式会社","Modis株式会社","株式会社テプコシステムズ","ハイブリィド株式会社【ウィルグループ＆スカイライトコンサルティング","株式会社メイテックフィルダーズ","株式会社メイテック","デロイトトーマツリップルマーク合同会社","株式会社すき家","株式会社ワールドインテック","株式会社リクルートスタッフィング","サンウエストホーム株式会社","株式会社ケアリッツ・テクノロジーズ","株式会社ビッグモーター","アイフル株式会社","株式会社ＦＰパートナー","株式会社エムツーエム","ゼネリックソリューション株式会社","株式会社HomeGrowin","株式会社ソフィアテック","株式会社ウィルオブ・ワーク","バリューアークコンサルティング株式会社","ゲームプロダクション株式会社","NRIシステムテクノ株式会社","株式会社Ｃ－ｍｉｎｄ","ジーエイチエス株式会社","ICONIC","株式会社ＳＣＲＩＰＴ","成田空港警備株式会社","株式会社メディアドゥ","株式会社オータム","株式会社アクセスネット","株式会社システム・クリエイト","株式会社Ｇｒｏｏｗ","株式会社ライジングサンセキュリティーサービス","フューチャーテクノロジー・コンサルティング株式会社","株式会社パイ・アール","abs株式会社","フォーザウィン株式会社","株式会社サウンドテクニカ","株式会社アイテック","エイム株式会社","ラーニンギフト株式会社","株式会社イズム","株式会社ＫＵＮＯ","株式会社シ・エム・シ","セントラル警備保障株式会社","ウィードファウスト株式会社","クムクム株式会社","TDCX","グローバルコムサービス株式会社","株式会社宇徳ビジネスサポート","アデコ株式会社","株式会社アイ・ディ・エイチ","株式会社日本テクノ開発","株式会社夢真","株式会社ジョーレン","ブックオフコーポレーション株式会社","株式会社ＪＣＤソリューション","有限会社ケーズドットコム","株式会社アムク","株式会社丸千代山岡家","ジブラルタ生命保険株式会社","共同エンジニアリング株式会社","大同生命保険株式会社","株式会社GainsLine","株式会社グローバー","富士フイルムシステムサービス株式会社","株式会社SEシェア","メットライフ生命保険株式会社","パーソルプロセス＆テクノロジー株式会社","エクスウェア株式会社","株式会社キカガク","Ｋ＆Ｋソリューション株式会社","株式会社テクノクレア","日本交通埼玉株式会社","株式会社FEDELTA","株式会社ウェム","アヴァント株式会社","千住金属工業株式会社","キーエンスソフトウェア株式会社","辰巳電子工業株式会社","株式会社ジャストワーク","株式会社エヌ・エイ・シー","山手交通株式会社","インターリンク株式会社","株式会社ワイズフューチャー","株式会社HES","ケイアイスター不動産株式会社","株式会社オービーシステム","株式会社ナミト","ハウンドジャパン株式会社","株式会社アイフリークモバイル","株式会社アジアピクチャーズエンタテインメント","株式会社Phoenixテクノロジーズ","株式会社要","株式会社アンフォルム","株式会社ザイナス","フューチャー・スクウェア株式会社","株式会社ＩＴコミュニケーションズ","株式会社あかツキ","東京ガスリックリビング株式会社","株式会社ブレイン・ラボ","株式会社ティーケーピー","株式会社oltre","株式会社コインパーク","株式会社エスエルジャパン","合同会社ナソリ","株式会社ソシアス","エムアイディ株式会社","株式会社ＩＴＰＭ","日本高圧洗浄株式会社","蔦交通株式会社","株式会社ブローウィッシュ","株式会社スカラコミュニケーションズ","株式会社システムサポート","株式会社アクロビジョン","イニシアティブソリューション株式会社","株式会社Branding","新明電材株式会社","株式会社ホンダカーズ埼玉中","アルテンジャパン株式会社","バリューテクノロジー株式会社","NEXT株式会社（虎ノ門本社)","新日本観光株式会社","株式会社さくらほりきり","アルタスソフトウェア株式会社","フォイスHRプロサービス株式会社","イエローテイルズ株式会社","株式会社シンカ","株式会社クリエーション・ビュー","朝日ソーラー株式会社","株式会社ラクスパートナーズ","株式会社A-urora","株式会社ステップ","株式会社チョーサンテクノ","株式会社花咲ソリューション","株式会社クロスパワー","株式会社truestar","株式会社トゥインクル","株式会社シティアスコムアイテック","株式会社ワイン・ラ・ターブル","シモハナ物流株式会社","株式会社ココロザシ","三松システムコンサルティング株式会社","株式会社ＲＥＶＯエンジニアリング","医療法人社団ＭＹメディカル","横浜トランスネット株式会社","株式会社エネサンス関東","株式会社シンサナミ","株式会社ライフコーポレーション","株式会社ネクステージ","株式会社アイビーカンパニー","株式会社サンマリエ","株式会社Ｔｉｍｏ","キヤノンビズアテンダ株式会社","株式会社シーメイプル","株式会社ＴＭＪ","TDCフューテック株式会社","ゼンプロジェクト株式会社","ジェイリース株式会社","アメージングアクティビティ株式会社","BaroqueWorks株式会社","NEXT株式会社（大阪支社・静岡支社)","株式会社サイゼント","LivEdge株式会社","株式会社グリームオーブ","株式会社TwinCompany","トライアロー株式会社","株式会社グルービージャーニー","オブザーブ株式会社","株式会社グッドワークコミュニケーションズ","株式会社フォトン算数クラブ","株式会社SALTO","株式会社セレマアシスト","株式会社丸和運輸機関","日本システムハウス株式会社","イオンクレジットサービス株式会社","株式会社EMD","ＲＩＺＡＰ株式会社","株式会社イマジカアロベイス","株式会社アイザワビルサービス","株式会社システムフリージア","株式会社プログレス","株式会社TheNewGate","株式会社ユニゾン・テクノロジー","オリックス自動車株式会社","ＨＪホールディングス株式会社","ソフィア総合研究所株式会社","株式会社NRC","株式会社LOHASTYLE","バルテス株式会社","株式会社データサポート","株式会社センス","株式会社シーエー・アドバンス","株式会社キーワードジャパン","ActCom株式会社","Happy","ヤフー株式会社","羽田エアポートセキュリティー株式会社","日の丸交通株式会社","株式会社サンウェル【Sanwell,","日本マルコ株式会社","株式会社カラビナ","株式会社カカクコム","オムロン","住友林業情報システム株式会社","ワン・アンド・カンパニー株式会社","株式会社オンテックス","株式会社インフィライズ","Ｓｋｙ株式会社","株式会社トップエンジニアリング","日建リース工業株式会社","東京福山通運グループ【合同募集】","医療法人社団同友会","株式会社ボルテックス","千葉構内タクシー株式会社","株式会社モトーレンティーアイ","株式会社レバレッジ","GMOソリューションパートナー株式会社","PwCコンサルティング合同会社","株式会社AGAIN","日本道路興運株式会社","オムロン株式会社","金森興業株式会社","シティコンピュータ株式会社","株式会社レソリューション","株式会社神戸製鋼所","株式会社シーディア","トヨタ自動車株式会社","株式会社リーディング・エッジ社","株式会社アシスト","株式会社イシカワコーポレーション","株式会社ジョブズコンストラクション","Ｓａｚｅ株式会社","株式会社ヤマシンホーム","株式会社リッチ","アクセラレイテッド・ソフトウェア・エンジニアリング合同会社","株式会社エス・エム・エス","株式会社D-Standing","株式会社日本ビジネスデータープロセシングセンター","株式会社ガイアコミュニケーションズ","株式会社アドバンスクリエイティブ/株式会社アドバンスワークス","日本交通横浜株式会社","株式会社クリア","全国農業協同組合連合会","株式会社Lecc","京セラ株式会社","日産自動車株式会社","テックコイン株式会社","株式会社シンメトリア","株式会社サイバーエージェント","株式会社ミアーズ","株式会社Liberta","アリババ株式会社","サイボウズ株式会社","株式会社ジラフ","株式会社無限の始まり","神奈中タクシー株式会社","豊玉タクシー株式会社","セレックバイオテック株式会社","株式会社静岡銀行","京葉コンピューターサービス株式会社","株式会社Ｒｏｏｍ１２","東洋交通株式会社","シームレスサービス株式会社","株式会社SPEED","株式会社三菱UFJ銀行","イケア・ジャパン株式会社","株式会社第一コンピュータサービス","株式会社ワールドコーポレーション","株式会社Crane&I","株式会社LainZ","三井不動産株式会社","株式会社セレクティ","株式会社エイトエンジニアリング","西華デジタルイメージ株式会社","株式会社プラウディア","株式会社マネジメントソリューションズ","東レ株式会社","株式会社アクロス・シティ","株式会社サン・マルタカ","協和警備保障株式会社","株式会社ＮＥＣＴ","H.R.I","株式会社LIFULL","株式会社ユームス","株式会社システムアイ","ニッカホーム関東株式会社","株式会社フラット","メディアリンク株式会社","ユニ・チャーム株式会社","株式会社サイコー","株式会社イマジカデジタルスケープ","株式会社ＵＲコミュニティ","株式会社シンプルウェイ","株式会社玉","株式会社TBM","株式会社アルゴビジネスサービス","株式会社エムケイエス","ラピードアクト株式会社","株式会社フレクト","ホーチキ株式会社","Ｔｅｃｈｎｏｃｒａｔｓ","株式会社ねぎしフードサービス","株式会社リクルートR&Dスタッフィング","アラコム株式会社","株式会社Dexall","株式会社ＷＥＤＧＥ","シミック・アッシュフィールド株式会社","株式会社Ｙ－Ｓ４","株式会社ディー・エヌ・エー","株式会社Level","株式会社スリーエス","小田急交通株式会社","楽天生命保険株式会社","日本ＰＭＣ株式会社","株式会社トライトキャリア","株式会社ウェディングボックス","ＡＳＫＵＬ","株式会社ココナラ","株式会社アイディーエス","株式会社セイル","株式会社いえらぶパートナーズ","バジンガ株式会社","株式会社ケイアイ","株式会社日立社会情報サービス","株式会社オズクリエイション","株式会社デバンス","株式会社スカイネット","株式会社全日警サービス神奈川","太平ビルサービス株式会社","株式会社C","株式会社エーアイスミス","有限会社サクセスフュージョン","Xerotta株式会社","株式会社レインオンファニー","株式会社リンクスタッフグループ","株式会社ティー・アンド・ユー","株式会社Ｏｎｅ","システムエンハンス合同会社","アラクサラネットワークス株式会社","株式会社テクノプラス","株式会社ベクトロジー","日清食品グループ(日清食品株式会社)","株式会社日立ソリューションズ","小林運輸株式会社","株式会社わだち大泉","株式会社日立システムズパワーサービス","株式会社システムエージェントジャパン","株式会社テックスレポート","株式会社カフェレオホールディングス","株式会社純アシスト","株式会社エイム","株式会社ウェーブ","株式会社シフォン","株式会社ディーワン","都築工業","未来開発株式会社","キリンメンテナンス・サービス株式会社","株式会社多摩流通","株式会社マルコム","株式会社日立システムズ","フルスタック株式会社","株式会社ベリアント","株式会社キューブアンドカンパニー","株式会社テックプロ","株式会社DHI","株式会社ユーテック","横浜無線タクシーグループ","株式会社アクトエンジニアリング","株式会社ビーテックインターナショナル","株式会社VOLLMONTホールディングス","ＴＡＣ株式会社","株式会社日立インフォメーションエンジニアリング","株式会社Bug.s","株式会社福井銀行","平和自動車交通株式会社","株式会社システムズアプローチ","株式会社キアフィード","株式会社ＡＣＴ","株式会社丸井グループ","株式会社アイセルネットワークス","株式会社ウイングノア","株式会社エム・ソフト","株式会社池田山エステート","BPOテクノロジー株式会社","フクダ","株式会社Ｄｏｏｒｓ","株式会社テックエデュケイションカンパニー","有限会社プリントメイト","株式会社日立アカデミー","株式会社キャップインフォ","ドリームジョイン株式会社","Marvel株式会社","ルネサス","株式会社ライフスクエア","株式会社アルスキューブ","株式会社トミーズコーポレーション","株式会社ポポンデッタ","株式会社イデアル総研","株式会社ビジネスソフト","株式会社ハートソフト","株式会社ｉ‐ＮＯＳ","株式会社ベストリンク","株式会社太陽ビルマネージメント","株式会社ZELXUS","株式会社PONTE","株式会社ｂｌｕｅ","株式会社末広システム","住友生命保険相互会社","Tres","株式会社グラブハーツ【CoCo壱番屋","株式会社ラグザス・クリエイト","株式会社ＳｅｅＤ","ペタビット株式会社","株式会社京福商店","株式会社ソフトハート","株式会社ヒューメインシステム","株式会社Ｎａｓｃｏｍ","株式会社キャリアイノベーション","株式会社ＡＮＯＴＨＥＲ","サン・エム・システム株式会社","株式会社村上組","株式会社ITreasure","株式会社中谷本舗","株式会社神戸クルーザー","生和不動産保証株式会社","日本コンセントリクス株式会社","株式会社アジャイルウェア","株式会社ホワイトホース","ワールドトランスシステム株式会社","株式会社エフ・エフ・エル","アマノ株式会社","日油株式会社","日本エンジニアリングソリューションズ株式会社（略称：NES)","フコク物産株式会社","CREFIL株式会社","ジェイ・ライン株式会社","株式会社コンタクト","ＴＥＴＲＡＰＯＴ株式会社","株式会社ケイプラン","株式会社イエスリフォーム","株式会社日本ハウスホールディングス","エヌ・ティ・ティ・システム開発株式会社","株式会社ウェットウェア","株式会社フルタイムシステム","株式会社ＷｅＳｔｙｌｅ","株式会社神戸物産","株式会社ｄａｂ","アジア株式会社","株式会社Ｂｌａｎｃ","株式会社オレンジ社","プロセスイノベーション株式会社","株式会社ネックスジャパン","アイデアル株式会社","株式会社ＴＯＹＯＤＡＴＡ","ミチル株式会社","株式会社BEELEAF","和光電気工事株式会社","有限会社藤管工業","オンライントラベル株式会社","株式会社ファーストコンテック","株式会社キャリアデザインセンターtype就活エージェント部","パーソルクロステクノロジー株式会社","株式会社AGEST","株式会社ジェイロック","ノヅック株式会社","株式会社ストーム","アエラホーム株式会社","株式会社テクノクリエイティブ","ＳＫｅｒ株式会社","株式会社チェルト","三楽建設株式会社","小川電機株式会社","ＪＨＲ株式会社","株式会社WASABI","リダクション株式会社","株式会社アイティーシー","株式会社エービーシステム","株式会社ユキオー","UT東芝株式会社","株式会社ファイン","長谷川運輸倉庫株式会社","株式会社HNS","株式会社ZIQCOM","ＱＬＣシステム株式会社","株式会社Japan","株式会社エヌエム・ヒューマテック","株式会社スクラムソフトウェア","株式会社読宣WEST","株式会社ベルクリック","カイゼンベース株式会社","ＭＳＰＣ株式会社","株式会社ビジネスブレーン","タカラスタンダード株式会社","株式会社日商","株式会社サワショウ","社会医療法人彩樹","株式会社グランド・ガーデン","株式会社オークレイ","株式会社オープンアップシステム","ＳＥモバイル・アンド・オンライン株式会社","株式会社松村組","アイレット株式会社","株式会社日本デジタル放送システムズ","株式会社BeForward","フラクタルシステムズ株式会社【ソフトウエア情報開発株式会社","株式会社レオパレス21","協栄企画システム株式会社","株式会社PRO技術","システム・アナライズ株式会社","株式会社豊和ソフト","株式会社アールツー","株式会社ペンタイン","株式会社ＣＡＲＥＳソリューションセンター","株式会社シムックスイニシアティブ","株式会社マジックウェイ","三研メディアプロダクト株式会社","セントラル技研株式会社","学校法人日本教育財団","株式会社日本経済新聞社","ソニーネットワークコミュニケーションズ株式会社","株式会社primeNumber","三菱総研ＤＣＳ株式会社","ソニーワイヤレスコミュニケーションズ株式会社","株式会社VRAIN","株式会社ＮＴＴデータビジネスシステムズ","みずほリサーチ&テクノロジーズ株式会社","株式会社アダストリア","株式会社ナガセ","伊藤忠インタラクティブ株式会社","浦安施設管理協同組合","SAPジャパン株式会社","医療法人社団上桜会","株式会社ベイカレント・コンサルティング","株式会社ジールコミュニケーションズ","SCSK株式会社","株式会社BeeX","株式会社3CA","ウルシステムズ株式会社","アドビ株式会社","サブライムコンサルティング株式会社","デジタルデータソリューション株式会社","パイオニア株式会社","株式会社パソナＪＯＢ","富士フイルムビジネスイノベーションジャパン株式会社","ミネベアミツミ株式会社","株式会社ＫＹＯＳＯ","EYストラテジー・アンド・コンサルティング株式会社","株式会社ブレインパッド","株式会社リツビ","ジュピターショップチャンネル株式会社","株式会社アイレップ","キッセイコムテック株式会社","株式会社Ｈｅｌｐｆｅｅｌ","西日本電信電話株式会社","キャップジェミニ株式会社","日本ＮＣＲ株式会社","株式会社ＡＢＥＪＡ","株式会社トップイノベーション","株式会社東洋新薬","キヤノン電子テクノロジー株式会社","株式会社東日本技術研究所","株式会社マネーパートナーズソリューションズ","株式会社日本総合研究所","STORES株式会社","株式会社wild","株式会社スカイウイル","株式会社インダストリー・ワン","SOMPOシステムズ株式会社","株式会社ウィルゲート","株式会社フィックスターズ","株式会社システムエグゼ","ガンホー・オンライン・エンターテイメント株式会社","ヨネックス株式会社","太陽グラントソントン・アドバイザーズ株式会社","東京海上日動システムズ株式会社","株式会社シー・ビー・ティ・ソリューションズ","NTTコム","株式会社インターネットイニシアティブ（IIJ）","株式会社ビジョン・コンサルティング","三菱地所","イオンスマートテクノロジー株式会社","株式会社Dirbato","株式会社バンダイナムコオンライン","株式会社カカクコム・インシュアランス","HENNGE株式会社","朝日インタラクティブ株式会社","株式会社イングリウッド","TISシステムサービス株式会社","株式会社DeepX","株式会社ラクス","マーサージャパン株式会社","エヌ・ティ・ティ・コムウェア株式会社","CTCテクノロジー株式会社","フリー株式会社","株式会社TVer","株式会社Amazia","株式会社博報堂アイ・スタジオ","楽天スーパーロジスティクス株式会社","エムスリーキャリア株式会社／開発部門","株式会社Algoage","株式会社アクセライト","住友化学株式会社","パーソルテクノロジースタッフ株式会社","イーテック株式会社","サイネオス・ヘルス・コマーシャル株式会社","47内装株式会社","株式会社クルイト","株式会社経営承継支援","テクマトリックス株式会社","ソニーペイメントサービス株式会社","インヴェンティット株式会社","株式会社ユニラボ","弥生株式会社","株式会社ＫＡＤＯＫＡＷＡ","株式会社Robot","株式会社ノーチラス・テクノロジーズ","株式会社キャリアデザインセンターtype転職エージェント事業部[ポジションマッチ登録]","株式会社MonotaRO","デジタルアーツ株式会社","株式会社ツリーベル","ＥＹストラテジー・アンド・コンサルティング株式会社","株式会社クランタス","株式会社MS-Japan","株式会社ＢＩＴＺ","株式会社CyberACE","キリンビジネスシステム株式会社","大正製薬株式会社","綜合警備保障株式会社","株式会社Ｍ＆Ａ総合研究所","株式会社インテグリティ・ヘルスケア","47株式会社","PwCあらた有限責任監査法人","株式会社レゾナック・ホールディングス","KDDI株式会社","株式会社アド・プロ","株式会社グラスト","株式会社野村総合研究所","クラウドエース株式会社","株式会社良品計画","アサヒクオリティーアンドイノベーションズ株式会社","ソニービズネットワークス株式会社","株式会社リクルート＜SUUMO領域＞","INTLOOP株式会社","株式会社スマイル","ユージーメンテナンス株式会社","株式会社アビスト","株式会社菱友システムズ","株式会社テンポイノベーション","株式会社バイトレ","株式会社日本Ｍ＆Ａセンター","株式会社リターンハート"]
    # company_list = ["株式会社Sunborn"]
    data = get_company_info_type.create_company_info(conmpany_name_list=company_list, output_flg=True)
    print(data)

