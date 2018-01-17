
from __future__ import (
    absolute_import,
    print_function,
)
from txsshsvr import (
    lobby,
    users,
)
from twisted.conch.recvline import HistoricRecvLine
from twisted.conch.insults.insults import TerminalProtocol
from twisted.python import log
from textwrap import dedent

def makeSSHApplicationProtocol(user_id):
    proto = SSHApplicationProtocol()
    proto.user_id = user_id
    return proto


class SSHApplicationProtocol(TerminalProtocol):
    CTRL_D = '\x04'
    user_id = None

    def connectionMade(self):
        TerminalProtocol.connectionMade(self)
        self._init_app_protocol()

    def keystrokeReceived(self, keyID, modifier):
        log.msg("key_id: {}, modifier: {}".format(keyID, modifier))
        if keyID == self.CTRL_D:
            self.terminal.loseConnection()
        else:
            self.app_protocol.handle_input(keyID, modifier)

    def terminalSize(self, width, height):
        log.msg("width: {}, height: {}".format(width, height))

    def unhandledControlSequence(self, seq):
        log.msg("unhandled control seq.")

    def _init_app_protocol(self):
        """
        Initialize the application protocol.
        """
        user_id = self.user_id
        entry = users.get_user_entry(user_id)
        need_init = False
        if entry.app_protocol is None:
            app_protocol = lobby.SSHLobbyProtocol()
            entry.app_protocol = app_protocol
            need_init = True
        app_protocol = entry.app_protocol
        app_protocol.terminal = self.terminal
        app_protocol.user_id = self.user_id
        self.app_protocol = app_protocol
        if need_init:
            app_protocol.initialize()
        else:
            self.terminal.reset()
            app_protocol.update_display()

    def connectionLost(self, reason):
        pass

