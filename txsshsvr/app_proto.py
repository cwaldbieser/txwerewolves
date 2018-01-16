
from __future__ import (
    absolute_import,
    print_function,
)
from txsshsvr import (
    lobby,
    users,
)
from twisted.conch.recvline import HistoricRecvLine
from twisted.python import log
from textwrap import dedent

def makeSSHApplicationProtocol(user_id):
    proto = SSHApplicationProtocol()
    proto.user_id = user_id
    return proto


class SSHApplicationProtocol(HistoricRecvLine):
    CTRL_D = '\x04'
    user_id = None

    def connectionMade(self):
        HistoricRecvLine.connectionMade(self)
        self.keyHandlers.update({
            self.CTRL_D: lambda: self.terminal.loseConnection()})
        try:
            self.handler.onConnect(self)
        except AttributeError:
            pass
        self._init_app_protocol()

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
        self._app_protocol = app_protocol
        if need_init:
            app_protocol.initialize()
        else:
            self.terminal.reset()
            app_protocol.show_banner()
            app_protocol.show_prompt()

    def connectionLost(self, reason):
        pass

    def lineReceived(self, line):
        line = line.strip()
        self._app_protocol.handle_line(line)


