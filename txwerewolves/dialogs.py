
from __future__ import division
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
        obj = self.parent()
        while True:
            if hasattr(obj, 'terminal'):
                return obj.terminal
            obj = obj.parent()

    @property
    def term_size(self):
        obj = self.parent()
        while True:
            if hasattr(obj, 'term_size'):
                return obj.term_size
            obj = obj.parent()

    @property
    def user_id(self):
        obj = self.parent()
        while True:
            if hasattr(obj, 'user_id'):
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
            CTRL-A   - Session admin mode.  Change game settings / restart.
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
 

class SessionAdminDialog(TermDialog):
    parent = None
    left = None
    top = None
    dlg_title = "Session Admin"
    werewolves = 2
    role_flags = None
    
    def draw(self):
        self._compute_coords()
        self._draw_box()
        self._draw_title()
        self._draw_instructions()
        self._draw_widgets()

    def _get_role_flags(self):
        role_flags = self.role_flags
        if role_flags is None:
            role_flags = {}
            self.role_flags = role_flags
            role_flags['seer'] = True
            role_flags['robber'] = True
            role_flags['troublemaker'] = True
            role_flags['minion'] = False
            role_flags['insomniac'] = False
            role_flags['hunter'] = False
            role_flags['tanner'] = False
        return role_flags

    def _compute_coords(self):
        tw, th = self.term_size
        self.width = int(tw * 0.8)
        self.height = int(th * 0.6)
        self.top = (th - self.height) // 2
        self.left = (tw - self.width) // 2
        self.equator = self.top + 7

    def _draw_title(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        title = self.dlg_title
        emca48 = A.bold[title, -A.bold[""]]
        text = assembleFormattedText(emca48)
        pos = dlg_left + (dlg_w - len(title)) // 2
        row = dlg_top
        terminal.cursorPosition(pos, row)
        terminal.write(text)

    def _draw_instructions(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        row = dlg_top + 2
        col_w = (dlg_w - 2) // 3
        pos = dlg_left + 2
        terminal.cursorPosition(pos, row)
        text = "0-9: Set number of werewolves."
        terminal.write(text)
        row += 1
        text = "s  : Toggle seer."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        row += 1
        text = "r  : Toggle robber."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        row += 1
        text = "t  : Toggle troublemaker."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        pos = dlg_left + 2 + col_w
        row = dlg_top + 2
        text = "m  : Toggle minion."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        row += 1
        text = "i  : Toggle insomniac."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        row += 1
        text = "i  : Toggle hunter."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        row += 1
        text = "T  : Toggle tanner."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
        pos = dlg_left + 2 + col_w * 2
        row = dlg_top + 2
        text = "^R : Reset game."
        terminal.cursorPosition(pos, row)
        terminal.write(text)
         
    def _draw_widgets(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        werewolves = self.werewolves
        role_flags = self._get_role_flags()
        row = self.equator + 2
        col_w = (dlg_w - 2) // 2

        def bool2yn(b):
            if b:
                return "Y"
            else:
                return "N"

        flags = [
            [("Seer:", bool2yn(role_flags['seer'])), ("Robber:", bool2yn(role_flags['robber']))],
            [("Troublemaker:", bool2yn(role_flags['troublemaker'])), ("Minion:", bool2yn(role_flags['minion']))],
            [("Insomniac:", bool2yn(role_flags['insomniac'])), ("Hunter:", bool2yn(role_flags['hunter']))],
            [("Tanner:", bool2yn(role_flags['tanner'])), ("Werewolves:", str(werewolves))],
        ] 
        label_len = 0
        for rinfo in flags:
            for label, flag in rinfo:
                label_len = max(label_len, len(label))
        label_len += 2
        for rinfo in flags:
            row += 1
            for n, (label, flag) in enumerate(rinfo):
                pos = dlg_left + 2 + n * col_w
                terminal.cursorPosition(pos, row)
                emca48 = A.bold[label, -A.bold[""]]
                text = assembleFormattedText(emca48) 
                terminal.write(text)                
                terminal.cursorPosition(pos + label_len, row)
                terminal.write(flag)

    def _draw_box(self):
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

    def _set_werewolves(self, count):
        self.werewolves = count

    def _toggle_flag(self, flag_name):
        self.role_flags[flag_name] = not self.role_flags[flag_name]

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        try:
            key_ord = ord(key_id)
            log.msg("key_ord: {}, mod: {}".format(key_ord, modifier))
        except TypeError as ex:
            key_ord = None
        log.msg("key_id: {}".format(key_id))
        if key_id == 'q' or ord(key_id) == 27:
            self.uninstall_dialog()
        elif key_id in '1234567890':
            self._set_werewolves(int(key_id))
        elif key_id == 's':
            self._toggle_flag('seer')
        elif key_id == 'r':
            self._toggle_flag('robber')
        elif key_id == 't':
            self._toggle_flag('troublemaker')
        elif key_id == 'm':
            self._toggle_flag('minion')
        elif key_id == 'i':
            self._toggle_flag('insomniac')
        elif key_id == 'h':
            self._toggle_flag('hunter')
        elif key_id == 'T':
            self._toggle_flag('tanner')
        return True


class BriefMessageDialog(TermDialog):
    parent = None
    left = None
    top = None
    brief_message = None
    _lines = None
    msg_duration = 5
    
    def draw(self):
        self._compute_coords()
        self._draw_box()
        self._draw_msg()
        self._schedule_close_dlg()

    def _schedule_close_dlg(self):
        self.parent().reactor.callLater(self.msg_duration, self.uninstall_dialog)

    def _compute_coords(self):
        tw, th = self.term_size
        self.width = int(tw * 0.5)
        msg = self.brief_message
        lines = wrap_paras(msg, self.width - 4)
        self._lines = lines
        self.height = min(int(th * 0.6), max(len(lines) + 2, 5))
        self.top = (th - self.height) // 2
        self.left = (tw - self.width) // 2

    def _draw_box(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
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
            terminal.write(" " * (dlg_w - 2))
            terminal.write(gchars.DBORDER_VERTICAL)
        row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (dlg_w - 2))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)

    def _draw_msg(self):
        terminal = self.terminal
        dlg_left = self.left
        dlg_top = self.top
        dlg_w = self.width
        dlg_h = self.height
        row = dlg_top + 1
        if len(self._lines) < dlg_h:
            row = (dlg_h - len(self._lines)) // 2 + dlg_top
        lines = self._lines
        msg_len = max(len(line) for line in lines)
        pos = dlg_left + (dlg_w - msg_len) // 2
        for line in lines:
            terminal.cursorPosition(pos, row)
            terminal.write(line)
            row += 1

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        try:
            key_ord = ord(key_id)
            log.msg("key_ord: {}, mod: {}".format(key_ord, modifier))
        except TypeError as ex:
            key_ord = None
        log.msg("key_id: {}".format(key_id))
        if key_id == 'q' or ord(key_id) == 27:
            self.uninstall_dialog()
        return True
