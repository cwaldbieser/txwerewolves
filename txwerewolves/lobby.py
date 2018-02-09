
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import weakref
from txwerewolves import (
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
from txwerewolves.apps import TerminalApplication
from txwerewolves.dialogs import (
   ChoosePlayerDialog, 
)
from txwerewolves.game import SSHGameProtocol
from txwerewolves import graphics_chars as gchars


class LobbyMachine(object):
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
        self._call_handler(self.handle_unjoined)

    @_machine.output()
    def _enter_invited(self):
        self._call_handler(self.handle_invited)

    @_machine.output()
    def _enter_accepted(self):
        self._call_handler(self.handle_accepted)

    @_machine.output()
    def _enter_waiting_for_accepts(self):
        self._call_handler(self.handle_waiting_for_accepts)

    @_machine.output()
    def _enter_session_started(self):
        self._call_handler(self.handle_session_started)

    @_machine.output()
    def _enter_invited(self):
        self._call_handler(self.handle_invited)

    # --------------
    # Event handlers
    # --------------

    @staticmethod
    def _call_handler(handler):
        if handler is not None:
            handler()

    handle_unjoined = None
    handle_invited = None
    handle_accepted = None
    handle_waiting_for_accepts = None
    handle_session_started = None
    handle_invited = None
    
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


class SSHLobbyProtocol(TerminalApplication):
    lobby = None
    instructions = ""
    commands = None
    status = ""
    output = ""

    @classmethod
    def make_instance(klass, reactor, terminal, user_id, parent):
        """
        Create a Lobby protocol.
        """
        lobby_machine = LobbyMachine()
        lobby = klass()
        lobby.lobby = lobby_machine
        lobby.reactor = reactor
        lobby.terminal = terminal
        lobby.user_id = user_id
        lobby.parent = weakref.ref(parent)
        lobby.commands = {}
        lobby_machine.handle_unjoined = lobby.handle_unjoined
        lobby_machine.handle_invited = lobby.handle_invited
        lobby_machine.handle_accepted = lobby.handle_accepted
        lobby_machine.handle_waiting_for_accepts = lobby.handle_waiting_for_accepts
        lobby_machine.handle_session_started = lobby.handle_session_started
        lobby_machine.handle_invited = lobby.handle_invited
        lobby_machine.initialize()
        return lobby

    def handle_input(self, key_id, modifiers):
        """
        Parse user input and act on commands.
        """
        if self.dialog is not None:
            self.dialog.handle_input(key_id, modifiers)
        else:
            func = self.commands.get(key_id)
            if func is None:
                return
            func()
        self.update_display()

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
        dialog.draw()

    def handle_unjoined(self):
        self.status = "You are not part of any session."
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (i)nvite players            - Invite players to join a session.
        * (l)ist                      - List players in the lobby.
        """)
        self.commands = {
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
        self.commands = {
            's': self._start_session,
            'i': self._invite,
            'j': self._show_joined,
            'c': self._cancel_session,
        }
        self.update_display()
    
    def handle_session_started(self):
        #proto = TodoProtocol()
        proto = SSHGameProtocol.make_protocol(
            user_id=self.user_id,
            terminal=self.terminal,
            term_size=self.term_size,
            parent=self.parent,
            reactor=self.reactor)
        self.parent().install_application(proto)

    def handle_invited(self):
        user_entry = users.get_user_entry(self.user_id)
        self.status = "Invited to join session '{}'.".format(
                user_entry.invited_id)
        self.instructions = textwrap.dedent("""\
        Valid commands are:
        * (a)ccept                    - Accept invitation to join session.
        * (r)eject                    - Reject invitation to join session.
        """)
        self.commands = {
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
        self.commands = {
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
            self.lobby.create_session()
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
        self.lobby.accept()

    def _reject_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        my_entry.invited_id = None
        self.lobby.reject()
        

    def _leave_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        my_entry.joined_id = None
        session_entry = session.get_entry(session_id)
        session_entry.members.discard(user_id)
        self.lobby.cancel()

    def _start_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        session_entry = session.get_entry(session_id)
        members = session_entry.members 
        for member in members:
            entry = users.get_user_entry(member)
            entry.app_protocol.lobby.start_session()

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
            entry.app_protocol.lobby.cancel()

    def signal_shutdown(self):
        """
        Allow the app to shutdown gracefully.
        """
        pass




