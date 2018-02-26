
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import weakref
from txwerewolves.interfaces import (
    IApplication,
    ITerminalApplication,
)
from txwerewolves import users
from twisted.python import log


class AppBase(object):
    """
    Base class for application objects.
    """
    appstate = None
    parent = None
    reactor = None
    user_id = None

    @property
    def avatar(self):
        user_id = self.user_id
        entry = users.get_user_entry(user_id)
        return entry.avatar

    

class TerminalAppBase(AppBase):
    """
    Base class for terminal application objects.
    """
    dialog = None
    term_size = (80, 24)
    terminal = None

    def install_dialog(self, dialog):
        dialog.parent = weakref.ref(self)
        self.dialog = dialog
        dialog.draw()

    def terminalSize(self, w, h):
        """
        Handles when the terminal is resized.
        """
        self.terminal.reset()
        self.term_size = (w, h)
        self.update_display()


class WebAppBase(AppBase):
    """
    Mixin for web applications.
    """
    dialog_handlers = None
    handlers = None

    def handle_input(self, command):
        """
        Parse user input and act on commands.
        """
        dialog_handlers = self.dialog_handlers
        if not dialog_handlers is None:
            f = dialog_handlers.get(command, None)
            if not f is None:
                f()
                return
        handlers = self.handlers
        f = handlers[command]
        f()  

