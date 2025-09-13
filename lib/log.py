from typing import Callable

LOG_CALLBACKS = []


def register_log_callback(callback: Callable[[str], None]):
    LOG_CALLBACKS.append(callback)


def debug(msg: str):
    print(msg)
    call_callbacks(msg)


def info(msg: str):
    print(msg)
    call_callbacks(msg)


def warning(msg: str):
    print(msg)
    call_callbacks(msg)


def error(msg: str):
    print(msg)
    call_callbacks(msg)


def call_callbacks(msg: str):
    for callback in LOG_CALLBACKS:
        callback(msg)
