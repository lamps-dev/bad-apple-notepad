"""Shared bits between the Windows and Linux editor backends."""


class EditorError(Exception):
    """Base class for every editor problem."""


class NoEditorFound(EditorError):
    """No text editor is installed / the window could never be located.

    This is fatal: there is nothing to draw into, so the caller should tell
    the user to install an editor and give up.
    """


class NoTextBackend(EditorError):
    """An editor exists, but nothing can push text into it.

    On Linux this means neither AT-SPI nor xdotool are usable. The caller is
    expected to warn, explain what to install, and fall back to terminal mode.
    """


class EditorDriver:
    """Tiny interface both backends implement."""

    name = "editor"

    def set_text(self, text):
        raise NotImplementedError

    def close(self):
        pass
