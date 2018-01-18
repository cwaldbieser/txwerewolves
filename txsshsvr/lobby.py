
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
        May still cancel invite at this point.
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
    def send_invitations(self):
        """
        Send invitations to other users.
        """

    @_machine.input()
    def received_invitation(self):
        """
        Received an invitation to join a session.
        """

    @_machine.input()
    def received_accepts(self):
        """
        Received acceptances to all invitations sent.
        """

    @_machine.input()
    def cancel(self):
        """
        Cancel an invitation or an acceptance.
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
    unjoined.upon(send_invitations, enter=waiting_for_accepts, outputs=[_enter_unjoined])
    unjoined.upon(received_invitation, enter=invited, outputs=[_enter_invited])
    waiting_for_accepts.upon(received_accepts, enter=session_started, outputs=[_enter_session_started])
    waiting_for_accepts.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])
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
    DVERT_T_LEFT = unichr(0x255F)
    DVERT_T_RIGHT = unichr(0x2562)
    HORIZONTAL = unichr(0x2500)
    terminal = None
    term_size = (80, 24)
    user_id = None

    def __init__(self):
        self.dialog_msg = None
        self.dialog_commands = None
        self.msg = ""
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

    def handle_unjoined(self):
        self.status = "You are not part of any session."
        self.msg = textwrap.dedent("""\
        Valid commands are:
        * (i)nvite players            - Invite players to join a session.
        * (l)ist                      - List players in the lobby.
        """)
        self.valid_commands = {
            'l': self._list_players,
            'i': self._invite,
        }
        self.update_display()
    
    def handle_invited(self):
        pass
    
    def handle_waiting_for_accepts(self):
        self.status = "Session {} - Waiting for Responses".format(
                user_entry.joined_id)
        self.msg = textwrap.dedent("""\
        Valid commands are:
        * (s)tart                     - Start the session with the current members.
        * (c)ancel                    - Cancel the session.
        """)
        self.valid_commands = {
            's': lambda args: self.terminal.write("Under construction."),
            'c': lambda args: self.terminal.write("Under construction."),
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
        self.output = '\n'.join(user_ids)
        self.update_display()

    def _invite(self):
        """
        Invite another player or players to join a session.
        """
        this_player = self.user_id()
        other_players = self._choose_invitees()
        user_entry = users.get_user_entry(this_player)
        session_entry = session.create_session()
        session_entry.owner = this_player
        session_entry.members.add(this_player)
        user_entry.joined_id = session_entry.session_id
        self.send_invitations()
        for user_id in player_set:
            user_entry = users.get_user_entry(user_id)
            user_entry.invited_id = session_entry.session_id
            user_entry.app_protocol.received_invitation()
        
    def _choose_invitees(self):
        """
        Create dialog for user to choose invitees.
        """
        this_user = self.user_id
        user_ids = users.get_user_ids()
        other_users = set([])
        for user_id in user_ids:
            if user_id == this.user:
                continue
            entry = users.get_user_entry(user_id)
            if entry.avatar is None:
                continue
            if entry.invited_id is not None:
                continue
            if entry.joined_id is not None:
                continue
            other_users.add(user_id)  
        self.dialog_commands = {

        }
        self.dialog_msg = ""

    def handle_input(self, key_id, modifiers):
        """
        Parse user input and act on commands.
        """
        if self.dialog_commands is not None:
            func = self.dialog_commands.get(key_id)
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

