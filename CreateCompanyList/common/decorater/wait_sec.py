import time
from functools import wraps


def wait_seconds(seconds=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if seconds:
                print(f"Waiting for {seconds} seconds...")
                time.sleep(seconds)
            return func(*args, **kwargs)
        return wrapper
    return decorator