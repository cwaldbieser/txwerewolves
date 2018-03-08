
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import collections
import json
import textwrap
import weakref
from txwerewolves import (
    session,
    users,
    utils,
)
from txwerewolves import graphics_chars as gchars
from txwerewolves.apps import (
    TerminalAppBase,
    WebAppBase,
)
from txwerewolves.dialogs import (
    ChatDialog,
    ChoosePlayerDialog, 
)
from txwerewolves.game import (
    SSHGameProtocol,
    WebGameProtocol,
)
from txwerewolves.interfaces import (
    ITerminalApplication,
    IWebApplication,
)
from automat import MethodicalMachine
from twisted.conch.insults.text import (
    attributes as A,
    assembleFormattedText,
)
from twisted.internet import defer
from twisted.python import log
from zope import interface
from zope.interface.declarations import implementer


class LobbyMachine(object):
    _machine = MethodicalMachine()

    # ---------------
    # Protocol states
    # ---------------

    TOKEN_START = "start"
    TOKEN_UNJOINED = "unjoined"
    TOKEN_WAITING_FOR_ACCEPTS = "waiting_for_accepts"
    TOKEN_INVITED = "invited"
    TOKEN_ACCEPTED = "accepted"
    TOKEN_SESSION_STARTED = "session_started"

    @_machine.state(serialized=TOKEN_START, initial=True)
    def start(self):
        """
        Initial state.
        """
    
    @_machine.state(serialized=TOKEN_UNJOINED)
    def unjoined(self):
        """
        Avatar has not joined a group session yet. 
        """

    @_machine.state(serialized=TOKEN_WAITING_FOR_ACCEPTS)
    def waiting_for_accepts(self):
        """
        User has invited others to a session, is waiting for them to accept.
        May cancel session and all accepts and outstanding invites.
        May choose to start session, cancelling any outstanding invites.
        """

    @_machine.state(serialized=TOKEN_INVITED)
    def invited(self):
        """
        User has been invited to a session.
        May accept or reject.
        """

    @_machine.state(serialized=TOKEN_ACCEPTED)
    def accepted(self):
        """
        User has accepted invitation to a session.  
        Is waiting for session to start.
        May still withdraw from invitation at this point.
        """ 

    @_machine.state(serialized=TOKEN_SESSION_STARTED)
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

    # -------------
    # Serialization
    # -------------
    
    @_machine.serializer()
    def savestate(self, state):
        return state

    @_machine.unserializer()
    def restorestate(self, state):
        log.msg("Restoring state `{}`.".format(state))
        self._fire_handler(state)
        return state

    def _fire_handler(self, state):
        log.msg("Entered _fire_handler()")
        if state == self.TOKEN_START:
            pass        
        elif state == self.TOKEN_UNJOINED:
            LobbyMachine._call_handler(self.handle_unjoined)
            log.msg("fired handle_unjoined().")
        elif state == self.TOKEN_WAITING_FOR_ACCEPTS:
            log.msg("about to fire handle_waiting_for_accepts().")
            LobbyMachine._call_handler(self.handle_waiting_for_accepts)
            log.msg("fired handle_waiting_for_accepts().")
        elif state == self.TOKEN_INVITED:
            LobbyMachine._call_handler(self.handle_invited)
            log.msg("fired handle_invited().")
        elif state == self.TOKEN_ACCEPTED:
            LobbyMachine._call_handler(self.handle_accepted)
            log.msg("fired handle_accepted().")
        elif state == self.TOKEN_SESSION_STARTED:
            LobbyMachine._call_handler(self.handle_session_started)
            log.msg("fired handle_session_started().")
        else:
            raise Exception("Unrecognized state '{}'.".format(state))


@implementer(ITerminalApplication)
class SSHLobbyProtocol(TerminalAppBase):
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

    def produce_compatible_application(self, iface, parent):
        """
        Produce an application with state similar to this one, but compatible
        with interface `iface`.
        """
        log.msg("entered produce_compatible_application().")
        if iface.providedBy(self):
            log.msg("iface is provided.  Returning self ...")
            return self
        if iface == IWebApplication:
            log.msg("iface is IWebApplication.")
            app = WebLobbyProtocol.make_instance(
                self.reactor,
                self.user_id,
                parent)
            log.msg("Created new app.")
            app.appstate.restorestate(self.lobby.savestate())
            log.msg("Updated state.")
            return app

    @property
    def appstate(self):
        """
        Application interface.
        Return the machine that drives the application.
        """
        return self.lobby

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

    def receive_signal(self, signal):
        """
        App interface.
        """
        sig_name, value = signal
        if sig_name == 'invite-cancelled':
            self.pending_invitations.discard(value)
            return
        if sig_name == 'chat-message':
            self._handle_new_chat()
            return
        log.msg("Received unknown signal '{}'.".format(sig_name))

    def _handle_new_chat(self):
        if not self.dialog is None:
            self.dialog.schedule_redraw()    
        else:
            self.new_chat_flag = True
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
        if self.new_chat_flag:
            msg = "New Chat Message"
            pos = (tw - len(msg)) // 2
            row = 14
            emca48 = A.bold[msg, -A.bold[""]]
            text = assembleFormattedText(emca48)
            terminal.cursorPosition(pos, row)
            terminal.write(text)

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
        dialog.schedule_redraw()

    def handle_unjoined(self):
        if not self.dialog is None:
            self.dialog.uninstall_dialog()
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
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None) and (not e.app_protocol is None)
        user_ids = [e.user_id for e in users.generate_user_entries(fltr=fltr)]
        log.msg("_list_players() user_ids: {}".format(user_ids))
        self.output.append("Available Players:\n{}".format('\n'.join(user_ids)))
        self.update_display()

    def _invite(self):
        """
        Invite another player or players to join a session.
        """
        this_player = self.user_id
        my_entry = users.get_user_entry(this_player)
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None) and (not e.app_protocol is None)
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
            avatar = user_entry.avatar
            avatar.send_message(msg)    

    def _reject_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.invited_id
        my_entry.invited_id = None
        self.lobby.reject()
        session_entry = session.get_entry(session_id)
        owner = session_entry.owner
        owner_entry = users.get_user_entry(owner)
        owner_avatar = owner_entry.avatar
        owner_avatar.send_app_signal(('invite-cancelled', user_id))
        owner_avatar.send_message("{} rejected your invitation.".format(user_id))

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
            avatar = user_entry.avatar
            avatar.send_message(msg)

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
            entry.avatar.send_message(msg)
            entry.app_protocol.appstate.cancel()
        pending_invitations = self.pending_invitations
        for player in pending_invitations:
            entry = users.get_user_entry(player)
            entry.joined_id = None
            entry.invited_id = None
            entry.avatar.send_message(msg)
            entry.app_protocol.appstate.revoke_invitation()
            
    def signal_shutdown(self):
        """
        Allow the app to shutdown gracefully.
        """
        pass


@implementer(IWebApplication)
class WebLobbyProtocol(WebAppBase):
    actions = None
    handlers = None
    lobby = None
    pending_invitations = None
    resource = "/lobby"
    status = ""

    @classmethod
    def make_instance(klass, reactor, user_id, parent):
        """
        Class factory.
        """
        lobby_machine = LobbyMachine()
        lobby = klass()
        lobby.lobby = lobby_machine
        lobby.reactor = reactor
        lobby.user_id = user_id
        lobby.parent = weakref.ref(parent)
        lobby.pending_invitations = set([])
        lobby.handlers = {}
        lobby.actions = []
        lobby_machine.handle_unjoined = lobby.handle_unjoined
        lobby_machine.handle_invited = lobby.handle_invited
        lobby_machine.handle_accepted = lobby.handle_accepted
        lobby_machine.handle_waiting_for_accepts = lobby.handle_waiting_for_accepts
        lobby_machine.handle_session_started = lobby.handle_session_started
        lobby_machine.handle_invited = lobby.handle_invited
        lobby_machine.initialize()
        return lobby

    def produce_compatible_application(self, iface, parent):
        """
        Produce an application with state similar to this one, but compatible
        with interface `iface`.
        """
        log.msg("entered produce_compatible_application().")
        if iface.providedBy(self):
            log.msg("iface is provided.  Returning self ...")
            return self
        if iface == ITerminalApplication:
            log.msg("iface is ITerminalApplication.")
            app = SSHLobbyProtocol.make_instance(
                self.reactor,
                parent.terminal,
                self.user_id,
                parent)
            log.msg("Created new app.")
            app.appstate.restorestate(self.lobby.savestate())
            log.msg("Updated state.")
            return app

    @property
    def appstate(self):
        """
        Application interface.
        Return the machine that drives the application.
        """
        return self.lobby

    def receive_signal(self, signal):
        """
        App interface.
        """
        sig_name, value = signal
        if sig_name == 'invite-cancelled':
            self.pending_invitations.discard(value)
            return
        if sig_name == 'chat-message':
            self._handle_new_chat()
            return
        log.msg("Received unknown signal '{}'.".format(sig_name))

    def _handle_new_chat(self):
        user_entry = users.get_user_entry(self.user_id)
        session_id = user_entry.joined_id
        if session_id is None:
            session_id = user_entry.invited_id
        session_entry = session.get_entry(session_id)
        output_buf = session_entry.chat_buf
        sender, msg = output_buf[-1]
        avatar = user_entry.avatar
        event = {'chat': {'sender': sender, 'message': msg}}
        event_str = json.dumps(event)
        avatar.send_event_to_client(event_str)
        
    def request_update(self, key):
        """
        Part of web application interface.
        Update the client based on the key provided.
        """
        if key == 'status':
            self._update_client_status()    
        elif key == 'actions':
            self._update_client_actions()

    def handle_unjoined(self):
        avatar = self.avatar
        self.status = 'You are not part of any session.'
        self._update_client_status()
        actions = [
            ('Invite players to join a session.', 0, 'Selecting a player ...'),
            ('List players in the lobby.', 1, 'Players listed.'),
        ]
        self.actions = actions
        self._update_client_actions()
        self.handlers = {
            1: self._list_players,
            0: self._invite,
        }
    
    def handle_waiting_for_accepts(self):
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        avatar = self.avatar
        self.status = "Session {} - Waiting for Responses".format(
                user_entry.joined_id)
        self._update_client_status()
        actions = [
            ('Start the session with the current members.', 0, 'Session started.'),
            ('Invite another player', 1, 'Selecting a player ...'),
            ('Show players that have joined the session.', 2, 'Members listed.'),
            ('Cancel the session.', 3, 'Session cancelled.'),
        ]
        self.actions = actions
        self._update_client_actions()
        self.handlers = {
            0 : self._start_session,
            1 : self._invite,
            2 : self._show_joined,
            3 : self._cancel_session,
        }
    
    def handle_session_started(self):
        proto = WebGameProtocol.make_protocol(
            user_id=self.user_id,
            parent=self.parent,
            reactor=self.reactor)
        avatar = self.avatar
        avatar.install_application(proto)

    def handle_invited(self):
        user_entry = users.get_user_entry(self.user_id)
        avatar = self.avatar
        status = "Invited to join session '{}'.".format(user_entry.invited_id)
        self.status = status
        self._update_client_status()
        actions = [
            ('Accept invitation to join session.', 0, 'Invitation accepted.'),
            ('Reject invitation to join session.', 1, 'Invitation rejected.'),
        ]
        self.actions = actions
        self._update_client_actions()
        self.handlers = {
            0: self._accept_invitation,
            1: self._reject_invitation,
        }

    def handle_accepted(self):
        my_entry = users.get_user_entry(self.user_id)
        self.status = "Joined session '{}'".format(my_entry.joined_id)
        self._update_client_status()
        actions = [
            ('List players that have joined the session.', 0, 'Members listed.'),
            ('Leave the session.', 1, 'You left the session.'),
        ]
        self.actions = actions
        self._update_client_actions()
        self.handlers = {
            0: self._show_joined,
            1: self._leave_session,
        }

    def _update_client_status(self):
        avatar = self.avatar
        command = {'status': self.status}
        command_string = json.dumps(command)
        avatar.send_event_to_client(command_string)

    def _update_client_actions(self):
        avatar = self.avatar
        actions = self.actions
        command = {'actions': actions}
        command_string = json.dumps(command)
        avatar.send_event_to_client(command_string)

    def _send_output_to_client(self, msg):
        avatar = self.avatar
        command = {'output': msg}
        command_string = json.dumps(command)
        avatar.send_event_to_client(command_string)
        
    def _list_players(self):
        """
        List players.
        """
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None) and (not e.app_protocol is None)
        user_ids = [e.user_id for e in users.generate_user_entries(fltr=fltr)]
        msg = "Available Players:\n{}".format('\n'.join(user_ids))
        self._send_output_to_client(msg)

    def _invite(self):
        """
        Invite another player or players to join a session.
        """
        this_player = self.user_id
        my_entry = users.get_user_entry(this_player)
        my_avatar = my_entry.avatar
        fltr = lambda e: (e.invited_id is None) and (e.joined_id is None)
        players = set([e.user_id for e in users.generate_user_entries(fltr=fltr)])
        players.discard(this_player)
        if len(players) == 0:
            my_avatar.send_message("No other players to invite at this time.")
            return
        players = list(players)
        players.sort()
        if my_entry.joined_id is None:
            session_entry = session.create_session()
            my_entry.joined_id = session_entry.session_id
            session_entry.owner = this_player
            session_entry.members.add(this_player)
            self.lobby.create_session()
        actions = [(player, n) for n, player in enumerate(players)]
        dialog_handlers = {}
        actions = []

        def _make_handler(player):

            def _invite():
                self._send_invite(player)

            return _invite

        for n, player in enumerate(players):
            actions.append((player, n, ''))
            dialog_handlers[n] = _make_handler(player)
        quit_action = len(actions)
        actions.append(("Stop inviting players", quit_action, ''))
        dialog_handlers[quit_action] = self._uninstall_dialog()
        self.dialog_handlers = dialog_handlers
        command = {
            'show-dialog': {
                'dialog-type': 'choose-players',
                'actions': actions,
            }
        }
        command_str = json.dumps(command)
        my_avatar.send_event_to_client(command_str)

    def _send_invite(self, player):
        my_avatar = self.avatar
        my_entry = users.get_user_entry(self.user_id)
        other_entry = users.get_user_entry(player)
        other_avatar = other_entry.avatar
        if other_entry.invited_id is not None:
            my_avatar.send_message("'{}' has already been invited to a session.".format(player))
            self._uninstall_dialog()
            return
        if other_entry.joined_id is not None:
            my_avatar.send_message("'{}' has already joined a session.".format(player))
            self._uninstall_dialog()
            return
        other_entry.invited_id = my_entry.joined_id
        other_entry.app_protocol.appstate.receive_invitation()
        my_avatar.send_message("Sent invite to '{}'.".format(player))
        self.lobby.send_invitation()
        self.pending_invitations.add(player)
        self._uninstall_dialog()

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
        msg = '\n'.join(lines)
        self._send_output_to_client(msg)

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
            avatar = user_entry.avatar
            avatar.send_message(msg)

    def _reject_invitation(self):
        user_id = self.user_id
        my_entry = users.get_user_entry(user_id)
        session_id = my_entry.invited_id
        my_entry.invited_id = None
        self.lobby.reject()
        session_entry = session.get_entry(session_id)
        owner = session_entry.owner
        owner_entry = users.get_user_entry(owner)
        owner_avatar = owner_entry.avatar
        owner_avatar.send_app_signal(('invite-cancelled', user_id))
        owner_avatar.send_message("{} rejected your invitation.".format(user_id))

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
            avatar = user_entry.avatar
            avatar.send_message(msg)

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
            entry.avatar.send_message(msg)
            entry.app_protocol.lobby.cancel()
        pending_invitations = self.pending_invitations
        for player in pending_invitations:
            entry = users.get_user_entry(player)
            entry.joined_id = None
            entry.invited_id = None
            entry.avatar.send_message(msg)
            entry.app_protocol.lobby.revoke_invitation()

    def _uninstall_dialog(self):
        self.dialog_handlers = None
        command = { 'hide-dialog': "" }
        command_str = json.dumps(command)
        self.avatar.send_event_to_client(command_str)


