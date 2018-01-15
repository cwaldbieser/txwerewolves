
from __future__ import (
    absolute_import,
    print_function,
)
from txsshsvr import (
    lobby,
    users,
)
import attr
from twisted.conch.recvline import HistoricRecvLine
from twisted.python import log
from textwrap import dedent

def makeSSHApplicationProtocol(avatar, *a, **k):
    proto = SSHApplicationProtocol()
    proto.avatar = avatar
    return proto


@attr.attrs
class Group(object):
    name = attr.attrib()
    owner = attr.attrib()
    members = attr.Factory(list)



class SSHApplicationProtocol(HistoricRecvLine):
    avatar = None
    prompt = "$"
    CTRL_D = '\x04'

    def connectionMade(self):
        users.add_avatar(self.avatar.user_id, self.avatar)
        self.avatar.terminal = self.terminal
        HistoricRecvLine.connectionMade(self)
        self.keyHandlers.update({
            self.CTRL_D: lambda: self.terminal.loseConnection()})
        try:
            self.handler.onConnect(self)
        except AttributeError:
            pass
        self._protocol_stack = []
        protocol = lobby.SSHLobbyProtocol(self.terminal)
        self._protocol = protocol
        protocol.avatar = self.avatar
        protocol.initialize()

    def connectionLost(self, reason):
        avatar = self.avatar
        users.remove_avatar(avatar.user_id, avatar)
        self.avatar.terminal = None

    def showPrompt(self):
        self.terminal.write("{0} ".format(self.prompt))

    def getCommandFunc(self, cmd):
        return getattr(self.handler, 'handle_{0}'.format(cmd), None)

    def lineReceived(self, line):
        line = line.strip()
        self._protocol.handle_line(line)


