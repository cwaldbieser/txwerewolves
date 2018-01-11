

from twisted.conch.recvline import HistoricRecvLine
from twisted.python import log
from textwrap import dedent

def makeSSHApplicationProtocol(avatar, *a, **k):
    proto = SSHApplicationProtocol()
    return proto


class SSHApplicationProtocol(HistoricRecvLine):

    prompt = "$"
    CTRL_D = '\x04'

    def connectionMade(self):
        HistoricRecvLine.connectionMade(self)
        self.keyHandlers.update({
            self.CTRL_D: lambda: self.terminal.loseConnection()})
        try:
            self.handler.onConnect(self)
        except AttributeError:
            pass
        self.showPrompt()

    def showPrompt(self):
        self.terminal.write("{0} ".format(self.prompt))

    def getCommandFunc(self, cmd):
        return getattr(self.handler, 'handle_{0}'.format(cmd), None)

    def lineReceived(self, line):
        line = line.strip()
        self.terminal.write("You said: {}".format(line))
        self.terminal.nextLine()
        self.showPrompt()



