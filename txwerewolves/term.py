
from __future__ import (
    absolute_import,
    print_function,
)
import weakref
from txwerewolves.interfaces import (
    ITerminalApplication,
)
from txwerewolves import (
    lobby,
    session,
    users,
)
from twisted.conch.recvline import HistoricRecvLine
from twisted.conch.insults.insults import TerminalProtocol
from twisted.python import log
from textwrap import dedent

def make_terminal_adapter(reactor, user_id):
    """
    Create an instance of a protocol that adapts the client terminal
    to a terminal-based application.
    """
    proto = TerminalAdapterProtocol()
    proto.reactor = reactor
    proto.user_id = user_id
    return proto


class TerminalAdapterProtocol(TerminalProtocol):
    CTRL_D = '\x04'
    CTRL_X = '\x18'
    reactor = None
    term_size = (80, 24)
    user_id = None

    def connectionMade(self):
        TerminalProtocol.connectionMade(self)
        self.init_app_protocol()

    def keystrokeReceived(self, key_id, modifier):
        key_id = key_id.decode('utf-8')
        try:
            key_ord = ord(key_id)
        except TypeError as ex:
            key_ord = None
        if key_id == self.CTRL_D:
            self.terminal.loseConnection()
        elif key_id == self.CTRL_X:
            self._shutdown_session()
        else:
            self.app_protocol.handle_input(key_id, modifier)

    def _shutdown_session(self):
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        session_id = user_entry.joined_id
        if session_id is None:
            return
        signal = ('shutdown', {'initiator': user_id})
        session.send_signal_to_members(session_id, signal)

    def terminalSize(self, width, height):
        log.msg("width: {}, height: {}".format(width, height))

    def unhandledControlSequence(self, seq):
        log.msg("unhandled control seq.")

    def init_app_protocol(self):
        """
        Initialize an application protocol if one does not exist.
        The application protocol will be term-based, and it is the
        thing the client will interact with.  E.g. a lobby or a game.
        All the other components exist only to connect the client
        to the app protocol.
        """
        user_id = self.user_id
        entry = users.get_user_entry(user_id)
        app_protocol = entry.app_protocol
        if app_protocol is None:
            app_protocol = lobby.SSHLobbyProtocol.make_instance(
                self.reactor,
                self.terminal,
                user_id,
                self
            )
        else:
            app_protocol = app_protocol.produce_compatible_application(
                ITerminalApplication, parent=self)
        entry.app_protocol = app_protocol
        app_protocol = entry.app_protocol
        app_protocol.reactor = self.reactor
        app_protocol.terminal = self.terminal
        app_protocol.term_size = self.term_size
        self.app_protocol = app_protocol
        app_protocol.parent = weakref.ref(self)

        def _request_refresh(terminal, app_protocol):
            terminal.reset()
            app_protocol.update_display()

        self.reactor.callLater(0, _request_refresh, self.terminal, app_protocol)

    def connectionLost(self, reason):
        pass

    def install_application(self, proto):
        if not ITerminalApplication.providedBy(proto):
            proto = proto.produce_compatible_application(
                ITerminalApplication, parent=self)
        self.app_protocol = proto
        self.terminal.reset()
        self.reactor.callLater(0, proto.update_display)
        user_entry = users.get_user_entry(self.user_id)
        user_entry.app_protocol = proto

