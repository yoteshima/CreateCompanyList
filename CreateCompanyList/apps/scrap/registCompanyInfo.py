# -*- coding: utf-8 -*-

import MySQLdb


class RegistCompanyInfo:

    def __init__(self, host, user, password, database):
        # ホスト名
        self.host = host
        # ユーザ名
        self.user = user
        # パスワード
        self.password = password
        # データベース名
        self.database = database


    def _init_database(self):
        """
        DB設定
        """
        connection = MySQLdb.connect(
            host = self.host,
            user = self.user,
            passwd = self.password,
            db = self.database
        )
        return connection.cursor()