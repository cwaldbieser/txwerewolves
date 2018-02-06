
from __future__ import (
    absolute_import,
    print_function,
)
import weakref
from txwerewolves import (
    lobby,
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
    reactor = None
    user_id = None

    def connectionMade(self):
        TerminalProtocol.connectionMade(self)
        self._init_app_protocol()

    def keystrokeReceived(self, key_id, modifier):
        try:
            key_ord = ord(key_id)
            log.msg("key_ord: {}, mod: {}".format(key_ord, modifier))
        except TypeError as ex:
            key_ord = None
        else:
            log.msg("key_id: {}".format(key_id))
        if key_id == self.CTRL_D:
            self.terminal.loseConnection()
        elif key_id == 'R':
            self.app_protocol.update_display()
        else:
            self.app_protocol.handle_input(key_id, modifier)

    def terminalSize(self, width, height):
        log.msg("width: {}, height: {}".format(width, height))

    def unhandledControlSequence(self, seq):
        log.msg("unhandled control seq.")

    def _init_app_protocol(self):
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
            entry.app_protocol = app_protocol
            app_protocol.initialize()
        app_protocol = entry.app_protocol
        app_protocol.reactor = self.reactor
        app_protocol.terminal = self.terminal
        self.app_protocol = app_protocol
        app_protocol.parent = weakref.ref(self)
        self.terminal.reset()
        app_protocol.update_display()

    def connectionLost(self, reason):
        pass

    def install_application_adapter(self, proto):
        self.app_protocol = proto
        self.terminal.reset()
        self.reactor.callLater(0, proto.update_display)
        user_entry = users.get_user_entry(self.user_id)
        user_entry.app_protocol = proto

