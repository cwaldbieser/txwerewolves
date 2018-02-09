
import weakref


class TerminalApplication(object):
    """
    Base class for terminal application objects.
    """
    dialog = None
    parent = None
    reactor = None
    term_size = (80, 24)
    terminal = None
    user_id = None

    def handle_input(self, key_id, modifiers):
        """
        Handle terminal input.
        """
        raise NotImplementedError()

    def install_dialog(self, dialog):
        dialog.parent = weakref.ref(self)
        self.dialog = dialog

    def signal_shutdown(self, **kwds):
        """
        Allow the app to shutdown gracefully.
        """
        raise NotImplementedError() 

    def terminalSize(self, w, h):
        """
        Handles when the terminal is resized.
        """
        self.terminal.reset()
        self.term_size = (w, h)
        self.update_display()

    def update_display(self):
        """
        Update the terminal display.
        """
        raise NotImplementedError() 

