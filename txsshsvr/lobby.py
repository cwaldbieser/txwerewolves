
from __future__ import (
    absolute_import,
    division,
    print_function,
)
from txsshsvr import (
    session,
    users,
)
import textwrap
from automat import MethodicalMachine
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)
from twisted.internet import defer
from twisted.python import log
from txsshsvr.todo import TodoProtocol
from txsshsvr.game import SSHGameProtocol
from txsshsvr import graphics_chars as gchars


class LobbyProtocol(object):
    _machine = MethodicalMachine()

    # ---------------
    # Protocol states
    # ---------------

    @_machine.state(initial=True)
    def start(self):
        """
        Initial state.
        """
    
    @_machine.state()
    def unjoined(self):
        """
        Avatar has not joined a group session yet. 
        """

    @_machine.state()
    def waiting_for_accepts(self):
        """
        User has invited others to a session, is waiting for them to accept.
        May cancel session and all accepts and outstanding invites.
        May choose to start session, cancelling any outstanding invites.
        """

    @_machine.state()
    def invited(self):
        """
        User has been invited to a session.
        May accept or reject.
        """

    @_machine.state()
    def accepted(self):
        """
        User has accepted invitation to a session.  
        Is waiting for session to start.
        May still withdraw from invitation at this point.
        """ 

    @_machine.state()
    def session_started(self):
        """
        The session has started.
        A new protcol can take over at this point.
        """

    # ------
    # Inputs
    # ------
   
    @_machine.input()
    def initialize(self):
        """
        Initialize the machine.
        """

    @_machine.input()
    def create_session(self):
        """
        Send an invitation to another player.
        """

    @_machine.input()
    def send_invitation(self):
        """
        Send an invitation to another player.
        """

    @_machine.input()
    def receive_invitation(self):
        """
        Receive an invitation to join a session.
        """

    @_machine.input()
    def start_session(self):
        """
        Received acceptances to all invitations sent.
        """

    @_machine.input()
    def cancel(self):
        """
        Cancel a session that has not yet been started if you are the owner.
        OR
        Cancel acceptance into a session that has not yet been started.
        """

    @_machine.input()
    def accept(self):
        """
        Accept an invitation.
        """

    @_machine.input()
    def reject(self):
        """
        Reject an invitation.
        """

    @_machine.input()
    def start_session(self):
        """
        Start a session.
        """

    # -------
    # Outputs
    # -------

    @_machine.output()
    def _enter_unjoined(self):
        self.handle_unjoined()

    @_machine.output()
    def _enter_invited(self):
        self.handle_invited()

    @_machine.output()
    def _enter_accepted(self):
        self.handle_accepted()

    @_machine.output()
    def _enter_waiting_for_accepts(self):
        self.handle_waiting_for_accepts()

    @_machine.output()
    def _enter_session_started(self):
        self.handle_session_started()

    @_machine.output()
    def _enter_invited(self):
        self.handle_invited()

    # --------------
    # Event handlers
    # --------------

    def handle_unjoined(self):
        raise NotImplementedError()
    
    def handle_invited(self):
        raise NotImplementedError()
    
    def handle_accepted(self):
        raise NotImplementedError()
    
    def handle_waiting_for_accepts(self):
        raise NotImplementedError()
    
    def handle_session_started(self):
        raise NotImplementedError()
    
    def handle_invited(self):
        raise NotImplementedError()
    
    # -----------
    # Transitions
    # -----------
    start.upon(initialize, enter=unjoined, outputs=[_enter_unjoined])
    unjoined.upon(create_session, enter=waiting_for_accepts, outputs=[_enter_waiting_for_accepts])
    unjoined.upon(receive_invitation, enter=invited, outputs=[_enter_invited])
    waiting_for_accepts.upon(start_session, enter=session_started, outputs=[_enter_session_started])
    waiting_for_accepts.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])
    waiting_for_accepts.upon(send_invitation, enter=waiting_for_accepts, outputs=[_enter_waiting_for_accepts])
    invited.upon(accept, enter=accepted, outputs=[_enter_accepted])
    invited.upon(reject, enter=unjoined, outputs=[_enter_unjoined])
    accepted.upon(start_session, enter=session_started, outputs=[_enter_session_started])
    accepted.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])


class SSHLobbyProtocol(LobbyProtocol):
    parent = None
    terminal = None
    term_size = (80, 24)
    user_id = None

    def __init__(self):
        self.dialog = None
        self.instructions = ""
        self.status = ""
        self.output = ""
        self.valid_commands = {}

    def update_display(self):
        """
        Update the status and message area. 
        """
        terminal = self.terminal
        terminal.reset()
        tw, th = self.term_size
        self._draw_border()
        self._update_player_area()
        self._update_status_area()
        self._update_instructions()
        self._show_output()
        self._show_dialog()
        terminal.cursorPosition(0, th - 1)

    def _draw_border(self):
        """
        Draw a border around the display area.
        """
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorHome()
        terminal.write(gchars.DBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(gchars.DBORDER_UP_RIGHT)
        for n in range(1, th):
            terminal.cursorPosition(0, n)
            terminal.write(gchars.DBORDER_VERTICAL)
            terminal.cursorPosition(tw-1, n)
            terminal.write(gchars.DBORDER_VERTICAL)
        terminal.cursorPosition(0, th - 1)
        terminal.write(gchars.DBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(gchars.DBORDER_DOWN_RIGHT)
        
    def _update_player_area(self):
        """
        Set the player name as the title of the window.
        """
        player = self.user_id
        terminal = self.terminal
        tw, th = self.term_size
        max_len = tw - 2
        if len(player) > max_len:
            player = player[:max_len]
        pos = (tw - len(player)) // 2
        terminal.cursorPosition(pos, 0)
        terminal.saveCursor()
        #reverseVideo, underline, bold
        player_text = assembleFormattedText(A.bold[A.fg.blue[player]])
        terminal.write(player_text)
        terminal.restoreCursor()

    def _update_status_area(self):
        """
        Update the status area with a brief message.
        """
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorPosition(0, 2)
        terminal.write(gchars.DVERT_T_LEFT)
        terminal.write(gchars.HORIZONTAL * (tw - 2))
        terminal.write(gchars.DVERT_T_RIGHT)
        status = self.status
        status_size = len(status)
        if status_size >= (tw - 2):
            status = status[:status_size - 2]
        pos = (tw - status_size) // 2
        terminal.cursorPosition(pos, 1)
        terminal.write(status)

    def _update_instructions(self):
        """
        Display instructions to the player.
        """
        terminal = self.terminal
        tw, th = self.term_size
        instructions = self.instructions
        text_lines = instructions.split("\n")
        instructions = []
        for text_line in text_lines:
            lines = textwrap.wrap(text_line, width=(tw - 4), replace_whitespace=False) 
            instructions.extend(lines)
        row = 4
        maxrow = 14
        maxwidth = max(len(line) for line in instructions)
        pos = (tw - (maxwidth + 2)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DHBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * maxwidth)
        terminal.write(gchars.DHBORDER_UP_RIGHT)
        title = "Instructions"
        terminal.cursorPosition((tw - len(title)) // 2, row)
        terminal.write(title)
        row += 1 
        for line in instructions:
            if row > maxrow:
                break
            terminal.cursorPosition(pos, row)
            terminal.write(gchars.VERTICAL)
            terminal.write(line)
            terminal.cursorPosition(pos + maxwidth + 1, row)
            terminal.write(gchars.VERTICAL)
            row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DHBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * maxwidth)
        terminal.write(gchars.DHBORDER_DOWN_RIGHT)

    def _show_output(self):
        """
        Show output.
        """
        terminal = self.terminal
        tw, th = self.term_size
        output = self.output
        row = 15
        terminal.cursorPosition(0, row)
        terminal.write(gchars.DVERT_T_LEFT)
        terminal.write(gchars.HORIZONTAL_DASHED * (tw - 2))
        terminal.write(gchars.DVERT_T_RIGHT)
        if output is None:
            return
        textlines = output.split("\n")
        termlines = []
        for textline in textlines:
            lines = textwrap.wrap(textline, width=(tw - 4), replace_whitespace=False) 
            termlines.extend(lines)
        row += 1
        for line in termlines:
            terminal.cursorPosition(2, row)
            terminal.write(line)
            row += 1

    def _show_dialog(self):
        """
        Show the dialog.
        """
        dialog = self.dialog
        if self.dialog is None:
            return        
        dialog.show_dialog()

    def handle_unjoined(self):
        self.status = "You are not part of any session."
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (i)nvite players            - Invite players to join a session.
        * (l)ist                      - List players in the lobby.
        """)
        self.valid_commands = {
            'l': self._list_players,
            'i': self._invite,
        }
        self.update_display()
    
    def handle_waiting_for_accepts(self):
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        self.status = "Session {} - Waiting for Responses".format(
                user_entry.joined_id)
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (s)tart                     - Start the session with the current members.
        * (i)nvite                    - Invite another player.
        * (j)oined                    - Show players that have joined the session.
        * (c)ancel                    - Cancel the session.
        """)
        self.valid_commands = {
            's': self._start_session,
            'i': self._invite,
            'j': self._show_joined,
            'c': self._cancel_session,
        }
        self.update_display()
    
    def handle_session_started(self):
        #proto = TodoProtocol()
        proto = SSHGameProtocol()
        proto.terminal = self.terminal
        proto.term_size = self.term_size
        proto.user_id = self.user_id
        proto.parent = self.parent
        self.parent().app_protocol = proto
        self.terminal.reset()
        self.reactor.callLater(0, proto.update_display)
   
    def handle_invited(self):
        user_entry = users.get_user_entry(self.user_id)
        self.status = "Invited to join session '{}'.".format(
                user_entry.invited_id)
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (a)ccept                    - Accept invitation to join session.
        * (r)eject                    - Reject invitation to join session.
        """)
        self.valid_commands = {
            'a': self._accept_invitation,
            'r': self._reject_invitation,
        }
        self.update_display()

    def handle_accepted(self):
        my_entry = users.get_user_entry(self.user_id)
        self.status = "Joined session '{}'".format(my_entry.joined_id)
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (j)oined                    - List players that have joined the session.
        * (c)ancel                    - Leave the session.
        """)
        self.valid_commands = {
            'j': self._show_joined,
            'c': self._leave_session,
        }
        self.update_display()

    def _list_players(self):
        """
        List players.
        """
        user_ids = users.get_user_ids()
        self.output = "Available Players:\n{}".format('\n'.join(user_ids))
        self.update_display()

    def _invite(self):
        """
        Invite another player or players to join a session.
        """
        this_player = self.user_id
        my_entry = users.get_user_entry(this_player)
        players = set(users.get_user_ids())
        players.discard(this_player)
        if len(players) == 0:
            self.output = "No other players to invite at this time."
            self.update_display()
            return
        players = list(players)
        players.sort()
        user_entry = users.get_user_entry(this_player)
        if my_entry.joined_id is None:
            session_entry = session.create_session()
            user_entry.joined_id = session_entry.session_id
            session_entry.owner = this_player
            session_entry.members.add(this_player)
            self.create_session()
        dialog = ChoosePlayerDialog()
        self.dialog = dialog
        self.dialog.parent = self
        self.dialog.players = players

    def _show_joined(self):
        """
        List the players that have joined the session.
        """
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        session_entry = session.get_entry(session_id)
        members = list(session_entry.members)
        members.sort()
        lines = []
        for n, player in enumerate(members): 
            lines.append("{}) {}".format(n + 1, player))
        self.output = '\n'.join(lines)
        self.update_display()

    def _accept_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.invited_id
        session_entry = session.get_entry(session_id)
        my_entry.joined_id = session_id
        my_entry.invited_id = None
        session_entry.members.add(user_id)
        self.accept()

    def _reject_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        my_entry.invited_id = None
        self.reject()
        

    def _leave_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        my_entry.joined_id = None
        session_entry = session.get_entry(session_id)
        session_entry.members.discard(user_id)
        self.cancel()

    def _start_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        session_entry = session.get_entry(session_id)
        members = session_entry.members 
        for member in members:
            entry = users.get_user_entry(member)
            entry.app_protocol.start_session()

    def _cancel_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        session_entry = session.get_entry(session_id)
        members = session_entry.members 
        session.destroy_entry(session_id)
        for member in members:
            entry = users.get_user_entry(member)
            entry.joined_id = None
            entry.invited_id = None
            entry.app_protocol.cancel()

    def handle_input(self, key_id, modifiers):
        """
        Parse user input and act on commands.
        """
        if self.dialog is not None:
            self.dialog.handle_input(key_id, modifiers)
        else:
            func = self.valid_commands.get(key_id)
            if func is None:
                return
            func()
        self.update_display()

    def terminalSize(self, w, h):
        """
        Handles when the terminal is resized.
        """
        self.terminal.reset()
        self.term_size = (w, h)
        self.update_display()


class AbstractDialog(object):
    """
    A dialog base class.
    """
    parent = None
    
    def show_dialog(self):
        raise NotImplementedError()

    def handle_input(self, key_id, modifiers):
        raise NotImplementedError()

class ChoosePlayerDialog(AbstractDialog):
    """
    A dialog for choosing a player.
    """
    title = " Choose Player ... "
    start_row = 16
    players = None
    player_pos = 0

    def show_dialog(self):
        parent = self.parent
        title = self.title
        terminal = self.parent.terminal
        tw, th = self.parent.term_size
        row = self.start_row
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
            """).format(gchars.UP_ARROW, gchars.DOWN_ARROW).encode('utf-8')
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
                player = assembleFormattedText(A.reverseVideo[player])
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
        parent = self.parent
        terminal = self.parent.terminal
        tw, th = self.parent.term_size
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
            'q': self._cancel_dialog,
        }
        func = dialog_commands.get(key_id, None)
        if func is not None:
            func()

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
        parent = self.parent
        user_id = self.parent.user_id
        my_entry = users.get_user_entry(user_id)
        player = self.players[self.player_pos]
        other_entry = users.get_user_entry(player)
        if other_entry.invited_id is not None:
            parent.output = "'{}' has already been invited to a session.".format(player)
            self._cancel_dialog()
            return
        if other_entry.joined_id is not None:
            parent.output = "'{}' has already joined a session.".format(player)
            self._cancel_dialog()
            return
        other_entry.invited_id = my_entry.joined_id
        other_entry.app_protocol.receive_invitation()
        parent.output = "Sent invite to '{}'.".format(player)
        my_entry.app_protocol.send_invitation()
        self.parent.dialog = None
        self.parent = None

    def _cancel_dialog(self):
        parent = self.parent
        self.parent.dialog = None
        self.parent = None
        parent.update_display()


