
from __future__ import division
import string
import textwrap
import weakref
from txwerewolves import (
    session,
    users,
)
from txwerewolves.utils import (
    wrap_paras,
)
from txwerewolves.compat import term_attrib_str
from txwerewolves import graphics_chars as gchars
from txwerewolves.werewolf import WerewolfGame
import six
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)
from twisted.python import log


class TermDialog(object):
    parent = None
    left = None
    top = None
    _redraw_id = None
    
    def draw(self):
        raise NotImplementedError()

    def schedule_redraw(self):
        reactor = self.parent().reactor
        if not self._redraw_id is None and self._redraw_id.active():
            return

        def _redraw():
            self.draw()
            self._redraw_id = None

        self._redraw_id = reactor.callLater(0, _redraw)

    def cancel_redraw(self):
        redraw_id = self._redraw_id
        if redraw_id is None:
            return
        if redraw_id.active():
            redraw_id.cancel()
        self.redraw_id = None

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        raise NotImplementedError()

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

    def uninstall_dialog(self):
        self.cancel_redraw()
        parent = self.parent()
        parent.dialog = None
        parent.update_display()

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
        msg = "Available Commands"
        emca48 = A.underline[msg, -A.underline[""]]
        heading = assembleFormattedText(emca48)
        text = textwrap.dedent("""\
            h        - This help.
            q or ESC - Quit dialog.
            TAB      - Toggle chat window. 
            CTRL-A   - Session admin mode.  Change game settings / restart.
            CTRL-X   - Quit to lobby.
            CTRL-D   - Disconnect (may reconnect later).
            """)
        lines = wrap_paras(text, help_w - 4)
        row_count = len(lines) + 2
        row = help_top + max((help_h - row_count) // 2, 1) 
        pos = help_left + (help_w - len(msg)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(heading)
        row += 2
        text_w = max(len(line) for line in lines)
        pos = help_left + (help_w - text_w) // 2
        for line in lines:
            row += 1
            terminal.cursorPosition(pos, row)
            if row == (help_top + help_h) - 2:
                terminal.write("...")
                break
            terminal.write(line)
        footer = "Press any key to close help."
        pos = help_left + (help_w - len(footer)) // 2
        row = help_top + help_h - 2
        terminal.cursorPosition(pos, row)
        emca48 = A.bold[footer, -A.bold[""]]
        text = assembleFormattedText(emca48)
        terminal.write(text)
        terminal.cursorPosition(0, th - 1)
        
    def handle_input(self, key_id, modifier):
        self.uninstall_dialog()
        return True


class ChatDialog(TermDialog):
    prompt = ">>>"
    input_buf = None
    output_buf = None
    pos = 0
    _redraw_prompt = None

    @classmethod
    def make_instance(klass, input_buf, output_buf):
        instance = klass()
        instance.input_buf = input_buf
        instance.output_buf = output_buf
        return instance

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

    def schedule_redraw_prompt(self):
        reactor = self.parent().reactor
        if not self._redraw_prompt is None and self._redraw_prompt.active():
            return

        def _redraw():
            self._compute_coords()
            self._draw_prompt()
            self._redraw_prompt = None

        self._redraw_prompt = reactor.callLater(0, _redraw)

    def cancel_redraw_prompt(self):
        redraw_prompt = self._redraw_prompt
        if redraw_prompt is None:
            return
        redraw_prompt.cancel()
        self._redraw_prompt = None

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
        self.schedule_redraw_prompt()

    def _arrow_left(self):
        pos = self.pos
        pos = max(pos - 1, 0)
        self.pos = pos
        self.schedule_redraw()

    def _backspace(self):
        buf = self.input_buf
        pos = self.pos
        pos = max(pos - 1, 0)
        self.pos = pos
        if len(buf) > 0:
            buf.pop(pos)
        self.schedule_redraw()

    def _send_msg(self):
        input_buf = self.input_buf
        output_buf = self.output_buf
        output_buf.append((self.user_id, ''.join(input_buf)))
        self._reset_input()
        self._signal_dialogs_redraw()
        self.schedule_redraw()
        
    def handle_input(self, key_id, modifier):
        try:
            key_ord = ord(key_id)
        except TypeError as ex:
            key_ord = None
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
        user_entry = users.get_user_entry(user_id)
        session_id = user_entry.joined_id or user_entry.invited_id
        if session_id is None:
            self.uninstall_dialog()
            return
        signal = ('chat-message', {'sender': self.user_id})
        session.send_signal_to_members(session_id, signal, include_invited=True, exclude=set([user_id]))

    def uninstall_dialog(self):
        self.cancel_redraw_prompt()
        super(ChatDialog, self).uninstall_dialog()
 

class SessionAdminDialog(TermDialog):
    parent = None
    left = None
    top = None
    dlg_title = "Session Admin"
    werewolves = 2
    role_flags = None
    _settings = None

    @classmethod
    def make_dialog(klass, settings):
        instance = klass()
        instance._settings = settings
        return instance
    
    def draw(self):
        self._compute_coords()
        draw_dialog_frame(self)
        self._draw_title()
        self._draw_instructions()
        self._draw_widgets()
        self.set_cursor_pos()

    def _get_role_flags(self):
        role_flags = self.role_flags
        if role_flags is None:
            role_flags = {}
            self.role_flags = role_flags
            settings = self._settings
            roles = settings.roles
            wg = WerewolfGame
            role_flags['seer'] = (wg.CARD_SEER in roles)
            role_flags['robber'] = (wg.CARD_ROBBER in roles)
            role_flags['troublemaker'] = (wg.CARD_TROUBLEMAKER in roles)
            role_flags['minion'] = (wg.CARD_MINION in roles)
            role_flags['insomniac'] = (wg.CARD_INSOMNIAC in roles)
            role_flags['hunter'] = (wg.CARD_HUNTER in roles)
            role_flags['tanner'] = (wg.CARD_TANNER in roles)
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

    def _set_werewolves(self, count):
        self.werewolves = count

    def _toggle_flag(self, flag_name):
        self.role_flags[flag_name] = not self.role_flags[flag_name]

    def _reset_game(self):
        role_flags = self._get_role_flags()
        werewolves = self.werewolves
        wg = WerewolfGame
        deck = set([])
        roles = [
            ('seer', wg.CARD_SEER),
            ('robber', wg.CARD_ROBBER),
            ('troublemaker', wg.CARD_TROUBLEMAKER),
            ('minion', wg.CARD_MINION),
            ('insomniac', wg.CARD_INSOMNIAC),
            ('hunter', wg.CARD_HUNTER),
            ('tanner', wg.CARD_TANNER),
        ]
        for name, card in roles:
            if role_flags[name]:
                deck.add(card)
        self._settings.roles = set(deck)
        self._settings.werewolves = werewolves
        parent = self.parent()
        user_id = parent.user_id
        make_protocol = parent.__class__.make_protocol
        user_entry = users.get_user_entry(user_id)
        app_protocol = user_entry.app_protocol
        proto = make_protocol(
            user_id=user_id,
            terminal=app_protocol.terminal,
            term_size=app_protocol.term_size,
            parent=app_protocol.parent,
            reactor=app_protocol.reactor,
            roles=deck,
            werewolves=werewolves,
            reset=True)
        session_id = user_entry.joined_id
        avatar = parent.avatar
        avatar.install_application(proto)
        signal = ('reset', {'sender': self.user_id})
        session.send_signal_to_members(session_id, signal) 
        self.uninstall_dialog()
        proto.update_display()

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        try:
            key_ord = ord(key_id)
        except TypeError as ex:
            key_ord = None
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
        elif key_ord == 18: # CTRL-R
            self._reset_game()
        self.schedule_redraw()
        return True

    def set_cursor_pos(self):
        tw, th = self.parent().term_size
        terminal = self.terminal
        terminal.cursorPosition(0, th - 1)
        return False


class BriefMessageDialog(TermDialog):
    parent = None
    left = None
    top = None
    brief_message = None
    _lines = None
    msg_duration = 5
    
    def draw(self):
        self._compute_coords()
        draw_dialog_frame(self)
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
        except TypeError as ex:
            key_ord = None
        self.uninstall_dialog()
        return True


class SystemMessageDialog(TermDialog):
    on_close = None
    left = None
    message = None
    msg_duration = -1
    parent = None
    top = None
    _lines = None

    @classmethod
    def make_dialog(klass, message, duration=-1, on_close=None):
        instance = klass()
        instance.message = message
        instance.msg_duration = duration
        instance.on_close = on_close
        return instance
    
    def draw(self):
        self._compute_coords()
        draw_dialog_frame(self)
        self._draw_msg()
        self._schedule_close_dlg()

    def _schedule_close_dlg(self):
        if self.msg_duration >= 0:
            self.parent().reactor.callLater(self.msg_duration, self.uninstall_dialog)

    def _compute_coords(self):
        tw, th = self.term_size
        self.width = int(tw * 0.5)
        msg = self.message
        lines = wrap_paras(msg, self.width - 4)
        self._lines = lines
        self.height = min(int(th * 0.6), max(len(lines) + 2, 5))
        self.top = (th - self.height) // 2
        self.left = (tw - self.width) // 2

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

    def _quit(self):
        self.uninstall_dialog()
        on_close = self.on_close
        if on_close is not None:
            on_close()

    def handle_input(self, key_id, modifier):
        """
        Handle input and return True
        OR
        return False for previous handler
        """
        try:
            key_ord = ord(key_id)
        except TypeError as ex:
            key_ord = None
        if key_id in ' q\r' or ord(key_id) == 27:
            self._quit()
        return True


class ChoosePlayerDialog(TermDialog):
    """
    A dialog for choosing a player.
    """
    title = " Choose Player ... "
    top = 16
    players = None
    player_pos = 0

    @classmethod
    def make_dialog(klass, players):
        instance = klass()
        instance.players = players
        return instance

    def draw(self):
        parent = self.parent()
        title = self.title
        terminal = parent.terminal
        tw, th = parent.term_size
        row = self.top
        dialog_x = 2
        dialog_w = tw - 4
        pos = dialog_x
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 6))
        terminal.write(gchars.DBORDER_UP_RIGHT)
        pos = (tw - len(title)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(title)
        msg = textwrap.dedent(u"""\
            {} - Scroll up       {}   - Scroll down
            i - invite player   q - cancel 
            """).format(gchars.UP_ARROW, gchars.DOWN_ARROW).encode('utf-8').decode('utf-8')
        textlines = msg.split("\n")
        termlines = []
        for textline in textlines:
            lines = textwrap.wrap(textline, width=(tw - 4), replace_whitespace=False) 
            termlines.extend(lines)
        maxw = max(len(line) for line in termlines)
        row += 1
        self._blank_dialog_line(row)
        row += 1
        pos = (tw - maxw) // 2
        for line in termlines:
            self._blank_dialog_line(row)
            terminal.cursorPosition(pos, row)
            terminal.write(line)
            row += 1
        self._blank_dialog_line(row)
        row += 1
        self._blank_dialog_line(row)
        players = self.players
        player_count = len(players)
        player_pos = self.player_pos
        for n in range(player_pos-1, player_pos+2):
            if n < 0 or n >= player_count:
                player = " "
            else:
                player = players[n]
            row += 1
            self._blank_dialog_line(row)
            pos = (tw - len(player)) // 2
            terminal.cursorPosition(pos, row)
            if n == player_pos:
                player = assembleFormattedText(A.reverseVideo[term_attrib_str(player)])
            terminal.saveCursor()
            terminal.write(player)
            terminal.restoreCursor()
        row += 1
        self._blank_dialog_line(row)
        row += 1
        pos = dialog_x
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 6))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)
        
    def _blank_dialog_line(self, row):
        parent = self.parent()
        terminal = parent.terminal
        tw, th = parent.term_size
        dialog_x = 2
        dialog_w = tw - 4
        terminal.cursorPosition(dialog_x, row)
        terminal.write(gchars.DBORDER_VERTICAL)
        terminal.write(" " * (dialog_w - dialog_x))
        terminal.write(gchars.DBORDER_VERTICAL)

    def handle_input(self, key_id, modifiers):
        dialog_commands = {
            '[UP_ARROW]': self._cycle_players_up,
            '[DOWN_ARROW]': self._cycle_players_down,
            'i': self._send_invite_to_player,
            'q': self.uninstall_dialog,
        }
        func = dialog_commands.get(key_id, None)
        if func is not None:
            func()
            return True
        return False

    def _cycle_players_up(self):
        players = self.players
        pos = self.player_pos
        pos -= 1
        if pos < 0:
            return
        else:
            self.player_pos = pos

    def _cycle_players_down(self):
        players = self.players
        pos = self.player_pos
        pos += 1
        if pos >= len(players):
            return
        else:
            self.player_pos = pos
        
    def _send_invite_to_player(self):
        my_lobby = self.parent()
        user_id = my_lobby.user_id
        my_entry = users.get_user_entry(user_id)
        my_avatar = my_entry.avatar
        player = self.players[self.player_pos]
        other_entry = users.get_user_entry(player)
        other_avatar = other_entry.avatar
        if other_entry.invited_id is not None:
            my_avatar.send_message("'{}' has already been invited to a session.".format(player))
            self.uninstall_dialog()
            return
        if other_entry.joined_id is not None:
            my_avatar.send_message("'{}' has already joined a session.".format(player))
            self.uninstall_dialog()
            return
        if other_entry.app_protocol is None:
            my_avatar.send_message("'{}' has left the lobby.".format(player))
            self.uninstall_dialog()
            return
        other_entry.invited_id = my_entry.joined_id
        other_entry.app_protocol.lobby.receive_invitation()
        my_avatar.send_message("Sent invite to '{}'.".format(player))
        my_lobby.lobby.send_invitation()
        my_lobby.pending_invitations.add(player)
        self.uninstall_dialog()


def draw_dialog_frame(dialog):
    """
    Draw a dialog frame.
    """
    terminal = dialog.terminal
    dlg_left = dialog.left
    dlg_top = dialog.top
    dlg_w = dialog.width
    dlg_h = dialog.height
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

