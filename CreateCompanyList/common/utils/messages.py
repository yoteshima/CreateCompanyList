import os
from enum import Enum
from typing import TypeVar, Sequence

from dotenv import load_dotenv
from slack_sdk.web import WebClient
from slack_sdk.webhook import WebhookClient
from slack_sdk.models.attachments import Attachment

# .env ファイルのロード
load_dotenv()


class LabelColor(Enum):
    red = ("#D00000", "error")
    green = ("#00FF00", "success")
    yellow = ("#ffff00", "warn")


    def __init__(
        self, 
        code: str,
        status: str,
    ) -> None:
        self.code = code
        self.status = status


    @classmethod
    def get_code_by_status(cls, status):
        for item in cls:
            if item.status == status:
                return item.code
        return None


class StatusIcon(Enum):
    error_icon = (":x:", "error")
    success_icon = (":white_check_mark:", "success")
    warn_icon = (":warning:", "warn")


    def __init__(
        self, 
        tag: str,
        status: str,
    ) -> None:
        self.tag = tag
        self.status = status


    @classmethod
    def get_icontag_by_status(cls, status):
        for item in cls:
            if item.status == status:
                return item.tag
        return None


class StatusTitle(Enum):
    success = ("正常", "success")
    error = ("異常", "error")
    warn = ("警告", "warn")


    def __init__(
        self, 
        title: str,
        status: str,
    ) -> None:
        self.title = title
        self.status = status


    @classmethod
    def get_title_by_status(cls, status):
        for item in cls:
            if item.status == status:
                return item.title
        return None
    

class SlackClientManager:
    """
    Slackの操作を行うクライアント
    """
    def __init__(self, webhooks: bool=True) -> None:
        if webhooks:
            slak_webhooks_url = os.getenv("SLACK_WEBHOOKS_URL")
            self.client = WebhookClient(url=slak_webhooks_url)
        else:
            slack_token = os.getenv("SLACK_API_TOKEN_P")
            self.client = WebClient(token=slack_token)


    def post_message(
        self,
        source: str,
        message: str,
        status: str="success"
    ) -> None:
        """メッセージを送信

        Args:
            source (str): 媒体名
            message (str): 送信メッセージ
            status (str, optional): 処理結果の種類.（success/error/warn） Defaults to "success".
        """
        icon = StatusIcon.get_icontag_by_status(status=status)
        title = StatusTitle.get_title_by_status(status=status)
        message_attachments = [
            {
                "fallback": f"【{source}】社名リスト作成の実行ステータス: {status}",
                "pretext": f"{source} から情報取得実行中",
                "color": LabelColor.get_code_by_status(status=status),
                "fields": [
                    {
                        "title": f"{icon} {title}",
                        "value": message
                    }
                ]
            }
        ]
        # メッセージ送信
        self.client.send(attachments=message_attachments)



if __name__ == "__main__":
    slack_manager = SlackClientManager()
    slack_manager.post_message(source="Fuma", message="処理を開始します。", status="success")
    slack_manager.post_message(source="Fuma", message="処理に失敗しました。", status="error")
    slack_manager.post_message(source="Fuma", message="ちょっと心配です。", status="warn")
