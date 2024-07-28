import random


def generate_interval(min: int = 60, max: int = 300) -> int:
    """ランダムに待機時間を生成

    Args:
        min (int, optional): 待機時間の下限(秒). Defaults to 60.
        max (int, optional): 待機時間の上限(秒). Defaults to 300.

    Returns:
        int: 待機時間(秒)
    """
    return random.randint(min, max)