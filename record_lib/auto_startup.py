from os.path import expandvars, join, isfile, dirname, split
from sys import executable, argv

from typing import Tuple, List

from lib import log as logger
from socket import gethostname

import pylnk3


def add_warp(string: str):
    string = string.strip('"')
    return f'"{string}"'


def get_launch_cmd() -> Tuple[str, List[str]]:
    if len(argv) == 1 and argv[0] != "-startup" and (not argv[0].endswith(".exe")):
        return executable, [add_warp(argv[0]), *argv[1:]]
    return executable, ["-startup"]


def set_auto_startup():
    lnk_path = join(expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"), "BSR Auto Startup.lnk")
    if isfile(lnk_path):
        return
    target_exe, args = get_launch_cmd()
    kwargs = {
        **({"work_dir": split(dirname(__file__))[0]} if target_exe.endswith("python.exe") or target_exe.endswith("pythonw.exe") else {})
    }
    pylnk3.for_file(target_exe, lnk_path, arguments=" ".join(args), **kwargs)


def set_auto_startup_no_error():
    try:
        if gethostname() == "Kanster-002":
            logger.info("识别为hite404的电脑，跳过设置开机自启")
            return
        set_auto_startup()
    except Exception as e:
        logger.error(f"设置开机自启动失败 -> {e.__class__.__name__}: {e}")


if __name__ == "__main__":
    set_auto_startup_no_error()
