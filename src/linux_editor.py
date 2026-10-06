"""Linux backend: finds a graphical text editor and shoves ASCII frames into it.

Linux has no WM_SETTEXT, so there are two ways to drive the editor:

1. AT-SPI (the accessibility bus). This is the proper analogue of WM_SETTEXT:
   it talks to the toolkit's accessible object and replaces the document text
   directly. It is display-server agnostic, so it works identically on Wayland
   and on X11. Needs PyGObject + the at-spi2 introspection data.

2. xdotool. X11 only, and jankier: select-all then paste (or type) into the
   focused window. Used only when AT-SPI is unavailable.

If neither works we raise NoTextBackend and let the caller drop to terminal
mode. If no editor is installed at all we raise NoEditorFound.
"""

import os
import shutil
import subprocess
import time

from editor_common import EditorDriver, NoEditorFound, NoTextBackend

# Preference order. KWrite first, then Kate, then whatever else is around.
# "args" are the flags needed to force a fresh window instead of reusing an
# already-running instance.
EDITORS = [
    {"bin": "kwrite", "label": "KWrite", "args": [], "atspi": "kwrite"},
    {"bin": "kate", "label": "Kate", "args": ["--new"], "atspi": "kate"},
    {"bin": "gnome-text-editor", "label": "GNOME Text Editor",
     "args": ["--new-window"], "atspi": "gnome-text-editor"},
    {"bin": "gedit", "label": "gedit", "args": ["--new-window"], "atspi": "gedit"},
    {"bin": "mousepad", "label": "Mousepad", "args": ["--disable-server"],
     "atspi": "mousepad"},
    {"bin": "xed", "label": "Xed", "args": ["--new-window"], "atspi": "xed"},
    {"bin": "pluma", "label": "Pluma", "args": ["--new-window"], "atspi": "pluma"},
    {"bin": "featherpad", "label": "FeatherPad", "args": [], "atspi": "featherpad"},
    {"bin": "notepadqq", "label": "Notepadqq", "args": [], "atspi": "notepadqq"},
    {"bin": "geany", "label": "Geany", "args": ["-i"], "atspi": "geany"},
    {"bin": "leafpad", "label": "Leafpad", "args": [], "atspi": "leafpad"},
]

INSTALL_HINT = (
    "no graphical text editor was found on your system.\n"
    "please install one and try again, for example:\n"
    "  Arch      : sudo pacman -S kwrite      (or kate)\n"
    "  Debian/Ubu: sudo apt install kwrite    (or kate / gedit)\n"
    "  Fedora    : sudo dnf install kwrite    (or kate)\n"
    "  openSUSE  : sudo zypper install kwrite (or kate)\n"
    "KWrite and Kate are the best supported, but gedit, GNOME Text Editor,\n"
    "Mousepad, Xed, Pluma, FeatherPad, Notepadqq, Geany and Leafpad also work."
)

ATSPI_HINT = (
    "AT-SPI (the accessibility bus) is not available, so frames cannot be\n"
    "pushed into the editor. install it with one of:\n"
    "  Arch      : sudo pacman -S python-gobject at-spi2-core\n"
    "  Debian/Ubu: sudo apt install python3-gi gir1.2-atspi-2.0 at-spi2-core\n"
    "  Fedora    : sudo dnf install python3-gobject at-spi2-core\n"
    "on GNOME you may also need:\n"
    "  gsettings set org.gnome.desktop.interface toolkit-accessibility true"
)


def detect_session():
    """Return 'wayland', 'x11' or 'unknown'."""
    session = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if session in ("wayland", "x11"):
        return session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def find_editor():
    """Return the first editor from EDITORS that exists on PATH."""
    for editor in EDITORS:
        path = shutil.which(editor["bin"])
        if path:
            found = dict(editor)
            found["path"] = path
            return found
    return None


def _accessibility_env():
    """Env that forces the toolkits to expose their accessible objects."""
    env = os.environ.copy()
    # Qt (KWrite / Kate / FeatherPad / Notepadqq)
    env["QT_ACCESSIBILITY"] = "1"
    env["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "1"
    # GTK (gedit / GNOME Text Editor / Mousepad / Xed / Pluma / Geany)
    env["GTK_MODULES"] = ":".join(
        part for part in (env.get("GTK_MODULES", ""), "gail", "atk-bridge") if part
    )
    env["GNOME_ACCESSIBILITY"] = "1"
    env["ACCESSIBILITY_ENABLED"] = "1"
    env["NO_AT_BRIDGE"] = "0"
    return env


def _enable_gnome_a11y():
    """Best-effort: flip the GNOME toolkit-accessibility switch on."""
    if not shutil.which("gsettings"):
        return
    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "toolkit-accessibility", "true"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
    except Exception:
        pass


# --------------------------------------------------------------------------
# AT-SPI backend
# --------------------------------------------------------------------------

def _load_atspi():
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except Exception:
        return None
    try:
        if Atspi.init() > 1:  # 0 = ok, 1 = already inited, 2 = failed
            return None
    except Exception:
        return None
    return Atspi


def _editable_iface(node):
    """Return the EditableText interface of an accessible, or None."""
    for attr in ("get_editable_text_iface", "get_editable_text"):
        getter = getattr(node, attr, None)
        if getter is None:
            continue
        try:
            iface = getter()
        except Exception:
            continue
        if iface is not None:
            return iface
    return None


def _find_editable(Atspi, node, depth=0, max_depth=12):
    """Depth-first walk looking for the first editable text widget."""
    if depth > max_depth:
        return None
    try:
        role = node.get_role()
    except Exception:
        role = None

    if role in (Atspi.Role.TEXT, Atspi.Role.ENTRY, Atspi.Role.DOCUMENT_TEXT,
                Atspi.Role.DOCUMENT_FRAME, Atspi.Role.PARAGRAPH):
        iface = _editable_iface(node)
        if iface is not None:
            return node, iface

    try:
        count = node.get_child_count()
    except Exception:
        return None

    for index in range(count):
        try:
            child = node.get_child_at_index(index)
        except Exception:
            continue
        if child is None:
            continue
        found = _find_editable(Atspi, child, depth + 1, max_depth)
        if found:
            return found
    return None


def _find_app(Atspi, pid, atspi_name):
    """Locate the launched editor on the accessibility bus."""
    try:
        desktop = Atspi.get_desktop(0)
        count = desktop.get_child_count()
    except Exception:
        return None

    by_name = None
    for index in range(count):
        try:
            app = desktop.get_child_at_index(index)
        except Exception:
            continue
        if app is None:
            continue

        # matching by pid is exact, so prefer it when the binding exposes it
        getter = getattr(app, "get_process_id", None)
        if getter is not None:
            try:
                if getter() == pid:
                    return app
            except Exception:
                pass

        try:
            name = (app.get_name() or "").lower()
        except Exception:
            name = ""
        if by_name is None and atspi_name in name.replace(" ", "-"):
            by_name = app

    return by_name


class AtspiDriver(EditorDriver):
    backend = "AT-SPI"

    def __init__(self, name, process, node, iface):
        self.name = name
        self._process = process
        self._node = node
        self._iface = iface

    def set_text(self, text):
        self._iface.set_text_contents(text)

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()


def _try_atspi(editor, process, timeout=15.0):
    Atspi = _load_atspi()
    if Atspi is None:
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        app = _find_app(Atspi, process.pid, editor["atspi"])
        if app is not None:
            found = _find_editable(Atspi, app)
            if found:
                node, iface = found
                driver = AtspiDriver(editor["label"], process, node, iface)
                try:
                    driver.set_text("")  # smoke test before we commit to it
                except Exception:
                    return None
                return driver
        time.sleep(0.4)
    return None


# --------------------------------------------------------------------------
# xdotool backend (X11 only)
# --------------------------------------------------------------------------

def _find_window_id(pid, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            out = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--pid", str(pid)],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            return None
        ids = [line.strip() for line in out.stdout.splitlines() if line.strip()]
        if ids:
            return ids[-1]
        time.sleep(0.4)
    return None


class XdotoolDriver(EditorDriver):
    backend = "xdotool"

    def __init__(self, name, process, window_id, clipboard):
        self.name = name
        self._process = process
        self._window = window_id
        self._clipboard = clipboard  # ["xclip", ...] / ["xsel", ...] / None

    def _paste(self, text):
        subprocess.run(self._clipboard, input=text, text=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=5)
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", self._window,
             "key", "--clearmodifiers", "ctrl+a", "key", "--clearmodifiers", "ctrl+v"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        )

    def _type(self, text):
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", self._window,
             "key", "--clearmodifiers", "ctrl+a",
             "type", "--clearmodifiers", "--delay", "0", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )

    def set_text(self, text):
        if self._clipboard:
            self._paste(text)
        else:
            self._type(text)

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()


def _clipboard_command():
    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    if shutil.which("xsel"):
        return ["xsel", "--clipboard", "--input"]
    return None


def _try_xdotool(editor, process, session):
    if session != "x11":
        return None
    if not shutil.which("xdotool"):
        return None
    window_id = _find_window_id(process.pid)
    if not window_id:
        return None
    return XdotoolDriver(editor["label"], process, window_id, _clipboard_command())


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def create_driver(verbose=True):
    """Launch an editor and return a driver that can push frames into it.

    Raises NoEditorFound if nothing is installed, NoTextBackend if an editor
    is running but neither AT-SPI nor xdotool can drive it.
    """
    session = detect_session()
    editor = find_editor()
    if editor is None:
        raise NoEditorFound(INSTALL_HINT)

    if verbose:
        print("session: {} | editor: {} ({})".format(
            session, editor["label"], editor["path"]))

    _enable_gnome_a11y()
    process = subprocess.Popen(
        [editor["path"]] + editor["args"],
        env=_accessibility_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)  # give the window a moment to map

    driver = _try_atspi(editor, process)
    if driver is not None:
        if verbose:
            print("using the AT-SPI backend")
        return driver

    if verbose:
        print("AT-SPI unavailable, trying xdotool...")
    driver = _try_xdotool(editor, process, session)
    if driver is not None:
        if verbose:
            print("using the xdotool backend (expect frame drops, it's slow)")
        return driver

    if process.poll() is None:
        process.terminate()

    if session == "wayland":
        extra = ("\nyou're on Wayland, so xdotool cannot be used as a fallback "
                 "(it is X11-only).")
    elif not shutil.which("xdotool"):
        extra = "\nxdotool isn't installed either, so there was no fallback."
    else:
        extra = "\nthe xdotool fallback couldn't find the editor's window either."

    raise NoTextBackend(ATSPI_HINT + extra)
