
import textwrap
from txwerewolves.utils import (
    wrap_paras,
)
from txwerewolves import graphics_chars as gchars
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)
from twisted.python import log


class TermDialog(object):
    parent = None
    left = None
    top = None
    
    def draw(self):
        raise NotImplementedError()

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        raise NotImplementedError()

    def uninstall_dialog(self):
        self.parent().dialog = None

    @property
    def terminal(self):
        log.msg("Getting terminal ...")
        obj = self.parent()
        while True:
            if hasattr(obj, 'terminal'):
                log.msg("Terminal found.")
                return obj.terminal
            obj = obj.parent()

    @property
    def term_size(self):
        log.msg("Getting term size ...")
        obj = self.parent()
        while True:
            if hasattr(obj, 'term_size'):
                log.msg("Term size found.")
                return obj.term_size
            obj = obj.parent()


class HelpDialog(TermDialog):

    def draw(self):
        """
        Show help.
        """
        terminal = self.terminal
        tw, th = self.term_size
        help_w = int(tw * 0.8)
        help_h = int(th * 0.6)
        help_top = (th - help_h) // 2
        help_left = (tw - help_w) // 2
        self.left = help_left
        self.top = help_top
        pos = help_left
        row = help_top
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (help_w - 2))
        terminal.write(gchars.DBORDER_UP_RIGHT)
        for n in range(help_h - 2):
            row += 1
            terminal.cursorPosition(pos, row)
            terminal.write(gchars.DBORDER_VERTICAL)
            terminal.write(" " * (help_w - 2))
            terminal.write(gchars.DBORDER_VERTICAL)
        row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (help_w - 2))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)
        row = help_top + help_h // 2
        msg = "Available Commands"
        pos = help_left + (help_w - len(msg)) // 2
        emca48 = A.underline[msg, -A.underline[""]]
        msg = assembleFormattedText(emca48)
        terminal.cursorPosition(pos, row)
        terminal.write(msg)
        text = textwrap.dedent("""\
            h        - This help.
            q or ESC - Quit dialog.
            TAB      - Toggle chat window. 
            """)
        lines = wrap_paras(text, help_w - 4)
        row += 1
        pos = help_left + 2
        for line in lines:
            row += 1
            terminal.cursorPosition(pos, row)
            if row == (help_top + help_h) - 2:
                terminal.write("...")
                break
            terminal.write(line)
        terminal.cursorPosition(0, th - 1)
        
    def handle_input(self, key_id, modifier):
        log.msg("key_id: {}, mod: {}".format(ord(key_id), modifier))
        if key_id == 'q' or ord(key_id) == 27:
            self.uninstall_dialog()
            return True
        return True


class ChatDialog(TermDialog):

    def draw(self):
        """
        Show chat window.
        """
        self._compute_coords()
        self._draw_bg()
        self._draw_prompt()
        self._cursor_home()

    def _compute_coords(self):
        tw, th = self.term_size
        self.width = int(tw * 0.8)
        self.height = int(th * 0.6)
        self.top = (th - self.height) // 2
        self.left = (tw - self.width) // 2
        self.equator = self.top + 2

    def _draw_prompt(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        equator = self.equator
        pos = dlg_left + 2
        row = dlg_top + 1
        prompt = ">>>"
        terminal.cursorPosition(pos, row)
        terminal.write(prompt) 

    def _draw_bg(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        equator = self.equator
        pos = dlg_left
        row = dlg_top
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (dlg_w - 2))
        terminal.write(gchars.DBORDER_UP_RIGHT)
        for n in range(dlg_h - 2):
            row += 1
            terminal.cursorPosition(pos, row)
            terminal.write(gchars.DBORDER_VERTICAL)
            if row != equator:
                terminal.write(" " * (dlg_w - 2))
            else:
                terminal.write(gchars.HORIZONTAL_DASHED * (dlg_w -2))
            terminal.write(gchars.DBORDER_VERTICAL)
        row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (dlg_w - 2))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)

    def _cursor_home(self):
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorPosition(0, th - 1)
        
    def handle_input(self, key_id, modifier):
        log.msg("key_id: {}, mod: {}".format(ord(key_id), modifier))
        if ord(key_id) == 9:
            self.uninstall_dialog()
            return True
        return True


