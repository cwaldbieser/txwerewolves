
import string
import textwrap
from txwerewolves import (
    session,
    users,
)
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

    def set_cursor_pos(self):
        return False

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

    @property
    def user_id(self):
        log.msg("Getting user_id size ...")
        obj = self.parent()
        while True:
            if hasattr(obj, 'user_id'):
                log.msg("user_id found.")
                return obj.user_id
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
    prompt = ">>>"
    input_buf = None
    output_buf = None
    pos = 0

    def draw(self):
        """
        Show chat window.
        """
        self._compute_coords()
        self._draw_bg()
        self._draw_prompt()
        self._position_input_cursor()

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
        prompt = self.prompt
        terminal.cursorPosition(pos, row)
        terminal.write(prompt) 
        input_buf = self.input_buf
        line = ''.join(input_buf)
        if line is not None:
            terminal.write(" ")
            terminal.write(line)
        output_buf = self.output_buf
        row = equator + 2
        pos = dlg_left + 2
        filled = False
        for user_id, msg in reversed(output_buf):
            prefix = "[{}]: ".format(user_id)
            prefix_len = len(prefix)
            lines = wrap_paras(prefix + msg, dlg_w - 4)
            terminal.cursorPosition(pos, row)
            first = False
            for line in lines:
                if not first:
                    line = line[prefix_len:]
                    emca48 = A.bold[prefix, -A.bold[""]] 
                    text = assembleFormattedText(emca48)
                    terminal.write(text)
                    first = False
                if row == (dlg_top + dlg_h - 2):
                    terminal.write("...")
                    filled = True
                    break
                terminal.write(line)
            row += 1
            if filled:
                break

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

    def _position_input_cursor(self):
        buf_pos = self.pos
        pos = self._get_input_home_pos() + buf_pos
        row = self.top + 1
        terminal = self.terminal
        terminal.cursorPosition(pos, row)

    def _get_input_home_pos(self):
        home_pos = self.left + 2 + len(self.prompt) + 1
        return home_pos
        
    def _reset_input(self):
        self.pos = 0
        buf = self.input_buf
        buf[:] = []

    def _echo(self, char):
        pos = self.pos
        buf = self.input_buf
        buf_left = buf[:pos]
        buf_right = buf[pos:]
        buf_left.append(char)
        buf_left.extend(buf_right)
        buf[:] = buf_left
        pos = self._get_input_home_pos() + self.pos
        terminal = self.terminal
        terminal.cursorPosition(pos, 1)
        self.pos += 1

    def _arrow_left(self):
        pos = self.pos
        pos = max(pos - 1, 0)
        self.pos = pos

    def _backspace(self):
        buf = self.input_buf
        pos = self.pos
        pos = max(pos - 1, 0)
        self.pos = pos
        if len(buf) > 0:
            buf.pop(pos)

    def _send_msg(self):
        input_buf = self.input_buf
        output_buf = self.output_buf
        output_buf.append((self.user_id, ''.join(input_buf)))
        self._reset_input()
        self._signal_dialogs_redraw()
        
    def handle_input(self, key_id, modifier):
        try:
            key_ord = ord(key_id)
            log.msg("key_ord: {}, mod: {}".format(key_ord, modifier))
        except TypeError as ex:
            key_ord = None
        log.msg("key_id: {}".format(key_id))
        if key_ord == 9:
            self.uninstall_dialog()
        elif key_ord == 127: #backspace
            self._backspace()
        elif key_id in string.printable and key_id not in '\t\n\r\x0b\x0c':
            self._echo(key_id)
        elif key_id == "\r":
            self._send_msg()
        elif key_id == '[LEFT_ARROW]':
            self._arrow_left()
        return True

    def set_cursor_pos(self):
        self._position_input_cursor()
        return True

    def _signal_dialogs_redraw(self):
        user_id = self.user_id
        game = self.parent().game
        session_id = game.session_id
        session_entry = session.get_entry(session_id)
        members = set(session_entry.members)
        members.discard(user_id)
        for player in members:
            user_entry = users.get_user_entry(player)
            app_protocol = user_entry.app_protocol
            
            def _make_redraw_dialog(app_protocol):
            
                def _redraw_dialog():
                    if not app_protocol.dialog is None:
                        app_protocol.dialog.draw()    
       
                return _redraw_dialog

            self.parent().reactor.callLater(0, _make_redraw_dialog(app_protocol))
 

