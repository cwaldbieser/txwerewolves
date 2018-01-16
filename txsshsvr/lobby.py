
from __future__ import (
    absolute_import,
    print_function,
)
from txsshsvr import users
import textwrap
from automat import MethodicalMachine


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
    prompt = "$"
    terminal = None
    user_id = None

    def __init__(self):
        self.valid_commands = {}
        self.banner = ""

    def show_banner(self):
        terminal = self.terminal
        terminal.nextLine()
        terminal.write(self.banner)
        terminal.nextLine()
    def handle_unjoined(self):
        terminal = self.terminal
        terminal.cursorHome()
        terminal.eraseLine()
        terminal.write(
            "STATUS: {}, you are not part of any session.".format(
                self.user_id))
        terminal.nextLine()
        self.banner = textwrap.dedent("""\
        Valid commands are:
        * invite player[, player ...] - Invite players to join a session.
        * list                        - List players in the lobby. 
        """)
        self.valid_commands = {
            'list': self._list_players,
            'invite': self._invite,
        }
        self.show_banner()
        self.show_prompt()
    
    def handle_invited(self):
        pass
    
    def handle_waiting_for_accepts(self):
        pass
    
    def handle_session_started(self):
        pass
    
    def handle_invited(self):
        pass

    def handle_accepted(self):
        pass

    def show_prompt(self):
        self.terminal.write("{0} ".format(self.prompt))

    def handle_line(self, line):
        """
        Parse user input and act on commands.
        """
        line = line.strip()
        if line == "":
            return
        words = line.split()
        command = words[0].lower()
        args = words[1:]
        func = self.valid_commands.get(command, lambda args: self._invalid_command(words))
        func(args)
        self.show_prompt()

    def _list_players(self, args):
        """
        List players.
        """
        user_ids = users.get_user_ids()
        for user_id in user_ids:
            self.terminal.write(user_id)
            self.terminal.nextLine()

    def _invite(self, args):
        """
        Invite another player or players to join a session.
        """
        terminal = self.terminal
        players = args
        this_player = self.user_id.lower()
        user_ids = users.get_user_ids()
        other_players = set([uid.lower() for uid in user_ids])
        other_players.discard(this_player)
        valid = True
        for user_id in players:
            user_id = user_id.lower()
            if user_id == this_player:
                terminal.write("Cannot invite yourself.")
                terminal.nextLine()
                valid = False
            elif not user_id in other_players:
                terminal.write("User '{}' is not logged in.".format(user_id))
                terminal.nextLine()
                valid = False
        if not valid:
            return
        player_set = set(other_players)
        player_set.add(this_player)
        for user_id in player_set:
            apply_to_user_terminals(
                user_id,
                'write',
                "This command is under construction ...")
            apply_to_user_terminals(
                user_id,
                'nextLine')
        
    def _invalid_command(self, args):
        """
        Command entered was invalid.
        """
        self.terminal.write("Invalid command: {}".format(args[0]))
        self.terminal.nextLine()


def apply_to_user_terminals(user_id, func_name, *args, **kwds):
    """
    Call a method on the terminals of all avatars associated with this
    user.
    """
    entry = users.get_user_entry(user_id)
    avatar = entry.avatar
    terminal = avatar.ssh_protocol.terminalProtocol.terminal
    f = getattr(terminal, func_name)
    f(*args, **kwds)

