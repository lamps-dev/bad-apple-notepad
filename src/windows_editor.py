"""Windows backend: drives the real Notepad window via WM_SETTEXT.

This is the original main.py logic, moved behind the same small driver
interface the Linux backend uses so main.py doesn't need to care which
platform it's on.
"""

import subprocess
import time

import win32api
import win32con
import win32gui

from editor_common import EditorDriver, NoEditorFound


def _find_notepad_window():
    hwnd = win32gui.FindWindow("Notepad", None)
    if hwnd:
        return hwnd

    # Windows 11's modern Notepad uses a different window class
    results = []

    def _collect(handle, out):
        if win32gui.IsWindowVisible(handle):
            title = win32gui.GetWindowText(handle)
            if "Notepad" in title or "Untitled" in title:
                out.append(handle)

    win32gui.EnumWindows(_collect, results)
    return results[0] if results else None


def _find_edit_control(hwnd):
    edit = win32gui.FindWindowEx(hwnd, None, "Edit", None)
    if edit:
        return edit

    # modern Notepad nests the edit control deeper -- search recursively
    def _walk(parent):
        child = None
        while True:
            child = win32gui.FindWindowEx(parent, child, None, None)
            if not child:
                return None
            if win32gui.GetClassName(child) in ("Edit", "RichEditD2DPT"):
                return child
            found = _walk(child)
            if found:
                return found

    return _walk(hwnd)


class NotepadDriver(EditorDriver):
    name = "Notepad"

    def __init__(self, process, hwnd, edit):
        self._process = process
        self._hwnd = hwnd
        self._edit = edit

    def set_text(self, text):
        win32api.SendMessage(self._edit, win32con.WM_SETTEXT, 0, text)

    def close(self):
        pass


def create_driver():
    """Launch Notepad and return a driver bound to its edit control."""
    process = subprocess.Popen(["notepad.exe"])
    time.sleep(2)  # wait for Notepad to open

    hwnd = _find_notepad_window()
    if not hwnd:
        raise NoEditorFound("could not find the Notepad window")

    edit = _find_edit_control(hwnd)
    if not edit:
        raise NoEditorFound(
            "could not find Notepad's edit control "
            "(hwnd={}, class={})".format(hwnd, win32gui.GetClassName(hwnd))
        )

    return NotepadDriver(process, hwnd, edit)
