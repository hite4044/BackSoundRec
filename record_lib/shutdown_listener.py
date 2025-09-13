import ctypes
from ctypes import wintypes
from typing import Callable, Any, Optional
from lib import log as logger

import win32con as con
import win32gui


# 加载user32.dll库
user32 = ctypes.WinDLL('user32', use_last_error=True)
ShutdownBlockReasonCreate = user32.ShutdownBlockReasonCreate
ShutdownBlockReasonCreate.argtypes = (wintypes.HWND, wintypes.LPCWSTR)
ShutdownBlockReasonCreate.restype = wintypes.BOOL
ShutdownBlockReasonDestroy = user32.ShutdownBlockReasonDestroy
ShutdownBlockReasonDestroy.argtypes = (wintypes.HWND,)
ShutdownBlockReasonDestroy.restype = wintypes.BOOL


class ShutdownListener:
    def __init__(self, title: str = "Shutdown Listener"):
        self.save_func = None
        self.hwnd = None
        self.title = title
        self.exec_func: bool = False
        self.is_shutdown: bool = False

    def create_window(self):  # 创建窗口
        user32.CreateWindowExW.argtypes = (
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
            wintypes.INT,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID
        )
        user32.CreateWindowExW.restype = wintypes.HWND
        self.hwnd = win32gui.CreateWindowEx(
            con.WS_EX_TOOLWINDOW,
            self.register_window_class(),
            self.title,
            con.WS_TILEDWINDOW,
            10000, 10000, 260, 180,
            None,
            None,
            None,
            None
        )
        win32gui.ShowWindow(self.hwnd, 1)
        win32gui.UpdateWindow(self.hwnd)
        ShutdownBlockReasonCreate(self.hwnd, ctypes.create_unicode_buffer("数据正在保存"))
        if not self.hwnd:
            raise ctypes.WinError()

    def start(self):
        self.create_window()
        win32gui.PumpMessages()

    # noinspection PyPropertyAccess
    def register_window_class(self) -> str:  # 注册窗口类
        win_cls = win32gui.WNDCLASS()
        win_cls.lpfnWndProc = self.wnd_proc
        win_cls.lpszClassName = "BackSoundRec_Shutdown_Listener"
        win_cls.style = con.CS_HREDRAW | con.CS_VREDRAW
        win_cls.hInstance = win32gui.GetModuleHandle(None)
        atom = win32gui.RegisterClass(win_cls)
        if not atom:
            raise ctypes.WinError()
        return "BackSoundRec_Shutdown_Listener"

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == con.WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        elif msg == con.WM_QUERYENDSESSION:
            logger.info("系统准备关机")
            logger.info("保存数据")
            if self.save_func:
                self.is_shutdown = True
                self.exec_func = True
                self.save_func()
                self.exec_func = False
            ShutdownBlockReasonDestroy(self.hwnd)
            return True
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def set_save_func(self, func: Optional[Callable[[], Any]]):
        if not self.exec_func:
            self.save_func = func


# Example usage
if __name__ == "__main__":
    listener = ShutdownListener()
    listener.start()
