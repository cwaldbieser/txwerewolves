
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import collections
import weakref
from txwerewolves import (
    session,
    users,
    utils,
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
    ChatDialog,
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
    def revoke_invitation(self):
        """
        Revoke an invitation to join a session.
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
    invited.upon(revoke_invitation, enter=unjoined, outputs=[_enter_unjoined])
    accepted.upon(start_session, enter=session_started, outputs=[_enter_session_started])
    accepted.upon(cancel, enter=unjoined, outputs=[_enter_unjoined])


class SSHLobbyProtocol(TerminalApplication):
    commands = None
    instructions = ""
    input_buf = None
    lobby = None
    new_chat_flag = False
    output = None
    pending_invitations = None
    status = ""

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
        lobby.output = collections.deque([], 25)
        lobby.pending_invitations = set([])
        lobby.input_buf = []
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
        ORD_TAB = 9
        handled = False
        dialog = self.dialog
        if not handled and not dialog is None:
            handled = dialog.handle_input(key_id, modifiers)
        if not handled and ord(key_id) == ORD_TAB:
            self._show_chat()
            handled = True
        if not handled and not self.commands is None:
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
        dialog = self.dialog
        if dialog is not None:
            handled = dialog.set_cursor_pos()
        else:
            handled = False
        if not handled:
            terminal.cursorPosition(0, th - 1)

    def _show_chat(self):
        input_buf = self.input_buf
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        session_id = None
        if not user_entry.joined_id is None:
            session_id = user_entry.joined_id
        elif not user_entry.invited_id is None:
            session_id = user_entry.invited_id
        if session_id is None:
            return
        session_entry = session.get_entry(session_id)
        output_buf = session_entry.chat_buf
        dialog = ChatDialog.make_instance(input_buf, output_buf)
        self.install_dialog(dialog)
        self.new_chat_flag = False

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
        title = " {} ".format(player)
        player_text = assembleFormattedText(A.bold[A.fg.blue[title]])
        terminal.write(player_text)
        terminal.restoreCursor()

    def _update_status_area(self):
        """
        Update the status area with a brief message.
        """
        terminal = self.terminal
        tw, th = self.term_size
        terminal.cursorPosition(0, 4)
        terminal.write(gchars.DVERT_T_LEFT)
        terminal.write(gchars.HORIZONTAL * (tw - 2))
        terminal.write(gchars.DVERT_T_RIGHT)
        status = self.status
        status_size = len(status)
        if status_size >= (tw - 2):
            status = status[:status_size - 2]
        pos = (tw - status_size) // 2
        terminal.cursorPosition(pos, 2)
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
            lines = utils.wrap_paras(text_line, width=(tw - 4)) 
            instructions.extend(lines)
        row = 6
        maxrow = 14
        maxwidth = max(len(line) for line in instructions)
        pos = (tw - (maxwidth + 4)) // 2
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DHBORDER_UP_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (maxwidth + 2))
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
            terminal.write(" ")
            terminal.write(line)
            terminal.write(" ")
            terminal.cursorPosition(pos + maxwidth + 3, row)
            terminal.write(gchars.VERTICAL)
            row += 1
        terminal.cursorPosition(pos, row)
        terminal.write(gchars.DHBORDER_DOWN_LEFT)
        terminal.write(gchars.DBORDER_HORIZONTAL * (maxwidth + 2))
        terminal.write(gchars.DHBORDER_DOWN_RIGHT)

    def _show_output(self):
        """
        Show output.
        """
        terminal = self.terminal
        tw, th = self.term_size
        output_w = tw - 6
        gutter_pos = 2
        pos = 4
        output = self.output
        row = 15
        max_row = th - 2
        terminal.cursorPosition(0, row)
        terminal.write(gchars.DVERT_T_LEFT)
        terminal.write(gchars.HORIZONTAL_DASHED * (tw - 2))
        terminal.write(gchars.DVERT_T_RIGHT)
        row += 1
        for event in reversed(output):
            lines = utils.wrap_paras(event, output_w)
            terminal.cursorPosition(gutter_pos, row)
            terminal.write("-")
            for line in lines:
                terminal.cursorPosition(pos, row)
                if row >= max_row:
                    terminal.write("...")
                    break
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
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None)
        user_ids = [e.user_id for e in users.generate_user_entries(fltr=fltr)]
        self.output.append("Available Players:\n{}".format('\n'.join(user_ids)))
        self.update_display()

    def _invite(self):
        """
        Invite another player or players to join a session.
        """
        this_player = self.user_id
        my_entry = users.get_user_entry(this_player)
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None)
        players = set([e.user_id for e in users.generate_user_entries(fltr=fltr)])
        players.discard(this_player)
        if len(players) == 0:
            self.output.append("No other players to invite at this time.")
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
        dialog = ChoosePlayerDialog.make_dialog(players)
        self.install_dialog(dialog)

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
        lines.append("The following players have joined the session:")
        for n, player in enumerate(members): 
            lines.append("{}) {}".format(n + 1, player))
        self.output.append('\n'.join(lines))
        self.update_display()

    def _accept_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.invited_id
        session_entry = session.get_entry(session_id)
        owner = session_entry.owner
        owner_entry = users.get_user_entry(owner)
        my_entry.joined_id = session_id
        my_entry.invited_id = None
        session_entry.members.add(user_id)
        self.lobby.accept()
        pending_invitations = owner_entry.app_protocol.pending_invitations
        pending_invitations.discard(user_id)
        members = set(session_entry.members)
        members.discard(user_id)
        members = members.union(pending_invitations)
        msg = "{} joined session {}.".format(user_id, session_id)
        for player in members:
            user_entry = users.get_user_entry(player)
            app_protocol = user_entry.app_protocol
            app_protocol.output.append(msg)    
            app_protocol.update_display()

    def _reject_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.invited_id
        my_entry.invited_id = None
        self.lobby.reject()
        session_entry = session.get_entry(session_id)
        owner = session_entry.owner
        owner_entry = users.get_user_entry(owner)
        owner_lobby = owner_entry.app_protocol
        owner_lobby.output.append("{} rejected your invitation.".format(user_id))
        owner_lobby.update_display() 

    def _leave_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        my_entry.joined_id = None
        session_entry = session.get_entry(session_id)
        session_entry.members.discard(user_id)
        self.lobby.cancel()
        members = set(session_entry.members)
        members.discard(user_id)
        msg = "{} left session {}.".format(user_id, session_id)
        for player in members:
            user_entry = users.get_user_entry(player)
            app_protocol = user_entry.app_protocol
            app_protocol.output.append(msg)    
            app_protocol.update_display()

    def _start_session(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.joined_id
        session_entry = session.get_entry(session_id)
        for player in self.pending_invitations:
            player_entry = users.get_user_entry(player)
            player_entry.app_protocol.lobby.revoke_invitation()
            msg = "Session '{}' was started.  Your invitation has been revoked.".format(session_id)
            player_entry.app_protocol.output.append(msg)
            player_entry.invited_id = None
            player_entry.app_protocol.update_display()
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
        msg = "{} cancelled the session.".format(user_id)
        for member in members:
            entry = users.get_user_entry(member)
            entry.joined_id = None
            entry.invited_id = None
            entry.app_protocol.output.append(msg)
            entry.app_protocol.lobby.cancel()
        pending_invitations = self.pending_invitations
        for player in pending_invitations:
            entry = users.get_user_entry(player)
            entry.app_protocol.output.append(msg)
            entry.app_protocol.lobby.revoke_invitation()
            
    def signal_shutdown(self):
        """
        Allow the app to shutdown gracefully.
        """
        pass




