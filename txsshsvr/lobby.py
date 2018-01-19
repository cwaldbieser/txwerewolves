
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
    unjoined.upon(send_invitation, enter=waiting_for_accepts, outputs=[_enter_waiting_for_accepts])
    unjoined.upon(receive_invitation, enter=invited, outputs=[_enter_invited])
    waiting_for_accepts.upon(start_session, enter=session_started, outputs=[_enter_session_started])
    waiting_for_accepts.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])
    waiting_for_accepts.upon(send_invitation, enter=waiting_for_accepts, outputs=[_enter_waiting_for_accepts])
    invited.upon(accept, enter=accepted, outputs=[_enter_accepted])
    invited.upon(reject, enter=unjoined, outputs=[_enter_unjoined])
    accepted.upon(start_session, enter=session_started, outputs=[_enter_session_started])
    accepted.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])


class SSHLobbyProtocol(LobbyProtocol):
    DBORDER_UP_LEFT = unichr(0x2554)
    DBORDER_UP_RIGHT = unichr(0x2557)
    DBORDER_DOWN_LEFT = unichr(0x255A)
    DBORDER_DOWN_RIGHT = unichr(0x255D)
    DBORDER_VERTICAL = unichr(0x2551)
    DBORDER_HORIZONTAL = unichr(0x2550)
    DHBORDER_UP_LEFT = unichr(0x2552)
    DHBORDER_UP_RIGHT = unichr(0x2555)
    DHBORDER_DOWN_LEFT = unichr(0x2558)
    DHBORDER_DOWN_RIGHT = unichr(0x255B)
    DVERT_T_LEFT = unichr(0x255F)
    DVERT_T_RIGHT = unichr(0x2562)
    HORIZONTAL = unichr(0x2500)
    VERTICAL = unichr(0x2502)
    HORIZONTAL_DASHED = unichr(0x254C)
    UP_ARROW = unichr(0x2B06)
    DOWN_ARROW = unichr(0x2B07)
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
        terminal.write(self.DBORDER_UP_LEFT)
        terminal.write(self.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(self.DBORDER_UP_RIGHT)
        for n in range(1, th):
            terminal.cursorPosition(0, n)
            terminal.write(self.DBORDER_VERTICAL)
            terminal.cursorPosition(tw-1, n)
            terminal.write(self.DBORDER_VERTICAL)
        terminal.cursorPosition(0, th - 1)
        terminal.write(self.DBORDER_DOWN_LEFT)
        terminal.write(self.DBORDER_HORIZONTAL * (tw - 2))
        terminal.write(self.DBORDER_DOWN_RIGHT)
        
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
        terminal.write(self.DVERT_T_LEFT)
        terminal.write(self.HORIZONTAL * (tw - 2))
        terminal.write(self.DVERT_T_RIGHT)
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
        terminal.write(self.DHBORDER_UP_LEFT)
        terminal.write(self.DBORDER_HORIZONTAL * maxwidth)
        terminal.write(self.DHBORDER_UP_RIGHT)
        title = "Instructions"
        terminal.cursorPosition((tw - len(title)) // 2, row)
        terminal.write(title)
        row += 1 
        for line in instructions:
            if row > maxrow:
                break
            terminal.cursorPosition(pos, row)
            terminal.write(self.VERTICAL)
            terminal.write(line)
            terminal.cursorPosition(pos + maxwidth + 1, row)
            terminal.write(self.VERTICAL)
            row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(self.DHBORDER_DOWN_LEFT)
        terminal.write(self.DBORDER_HORIZONTAL * maxwidth)
        terminal.write(self.DHBORDER_DOWN_RIGHT)

    def _show_output(self):
        """
        Show output.
        """
        terminal = self.terminal
        tw, th = self.term_size
        output = self.output
        row = 15
        terminal.cursorPosition(0, row)
        terminal.write(self.DVERT_T_LEFT)
        terminal.write(self.HORIZONTAL_DASHED * (tw - 2))
        terminal.write(self.DVERT_T_RIGHT)
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
        self.status = "Session {} - Waiting for Responses".format(
                user_entry.joined_id)
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (s)tart                     - Start the session with the current members.
        * (c)ancel                    - Cancel the session.
        """)
        self.valid_commands = {
            's': lambda args: "",
            'c': lambda args: "",
        }
        self.update_display()
    
    def handle_session_started(self):
        pass
   
    def handle_invited(self):
        self.status = "Invited to join session '{}'.".format(
                user_entry.invited_id)
        self.banner = textwrap.dedent("""\
        Valid commands are:
        * (a)ccept                    - Accept invitation to join session.
        * (r)eject                    - Reject invitation to join session.
        """)
        self.valid_commands = {
            'a': lambda args: self.terminal.write("Under construction."),
            'r': lambda args: self.terminal.write("Under construction."),
        }
        self.update_display()

    def handle_accepted(self):
        pass

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
        user_entry = users.get_user_entry(this_player)
        session_entry = session.create_session()
        session_entry.owner = this_player
        session_entry.members.add(this_player)
        dialog = ChoosePlayerDialog()
        self.dialog = dialog
        self.dialog.parent = self
        
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
    player = None

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
        terminal.write(parent.DBORDER_UP_LEFT)
        terminal.write(parent.DBORDER_HORIZONTAL * (tw - 6))
        terminal.write(parent.DBORDER_UP_RIGHT)
        pos = (tw - len(title)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(title)
        msg = textwrap.dedent(u"""\
            {} - Scroll up       {}   - Scroll down
            i - invite player   q - cancel 
            """).format(parent.UP_ARROW, parent.DOWN_ARROW).encode('utf-8')
        textlines = msg.split("\n")
        termlines = []
        for textline in textlines:
            lines = textwrap.wrap(textline, width=(tw - 4), replace_whitespace=False) 
            termlines.extend(lines)
        maxw = max(len(line) for line in termlines)
        row += 1
        terminal.cursorPosition(dialog_x, row)
        terminal.write(parent.DBORDER_VERTICAL)
        terminal.write(" " * (dialog_w - dialog_x))
        terminal.write(parent.DBORDER_VERTICAL)
        row += 1
        pos = (tw - maxw) // 2
        for line in termlines:
            terminal.cursorPosition(dialog_x, row)
            terminal.write(parent.DBORDER_VERTICAL)
            terminal.write(" " * (dialog_w - dialog_x))
            terminal.write(parent.DBORDER_VERTICAL)
            terminal.cursorPosition(pos, row)
            terminal.write(line)
            row += 1

    def handle_input(self, key_id, modifiers):
        log.msg("KEY_ID: {}".format(key_id))
        dialog_commands = {
            '[UP_ARROW]': self._cycle_players_up,
            '[DOWN_ARROW]': self._cycle_players_down,
            'i': self._send_invite_to_player,
            'q': self._cancel_dialog,
        }

    def _cycle_players_up(self):
        pass

    def _cycle_players_down(self):
        pass

    def _send_invite_to_player(self):
        pass

    def _cancel_dialog(self):
        parent = self.parent
        self.parent.dialog = None
        self.parent = None
        parent.update_display()

