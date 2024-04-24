import os
import re
from typing import Union, Optional, Generator, List, Tuple

import mysql.connector
from dotenv import load_dotenv

# .env ファイルのロード
load_dotenv()

class MariaDbManager:
    """
    MariaDBを操作するクラス
    """
    def __init__(self) -> None:
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")


    def generate_cursor(self) -> None:
        """DB接続

        Raises:
            e: _description_
        """
        try:
            # DB接続
            self.conn = mysql.connector.connect(
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                database=self.db_name
            )
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as e:
            # TODO エラーログ出力
            self.conn.rollback()
            raise e
        except Exception as error:
            print(error)


    def execute(self, sql: str) -> List[Union[Tuple[str], None]]:
        """SQL実行

        Args:
            sql (str): クエリ

        Raises:
            e: _description_

        Returns:
            Optional[Generator[MySQLCursorAbstract, None, None]]: _description_
        """
        results = []
        try:
            # SQL実行
            self.cursor.execute(sql)
            if re.match(r"^(INSERT|UPDATE|DELETE).*", sql, re.IGNORECASE):
                # 結果をコミット
                self.conn.commit()
            else:
                # 結果取得
                results = self.cursor.fetchall()
        except mysql.connector.Error as e:
            # TODO エラーログ出力
            self.conn.rollback()
            raise e
        finally:
            return results


    def close(self) -> None:
        """DB接続の切断
        """
        self.cursor.close()
        self.conn.close()
