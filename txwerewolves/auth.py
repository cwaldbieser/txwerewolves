
from __future__ import (
    absolute_import,
    print_function,
)
import uuid
from txwerewolves import users
from txwerewolves.term import make_terminal_adapter
from twisted.cred.portal import IRealm
from twisted.conch.avatar import ConchUser
from twisted.conch.insults.insults import ServerProtocol
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh.session import SSHSession, wrapProtocol
from twisted.python import log
from zope.interface import implements

class ServerProtocol2(ServerProtocol):
    """
    Like `tx.conch.insults.insults.ServerProtocol`, but with options.
    """
    clearOnExit = True

    def loseConnection(self):
        if self.clearOnExit:
            self.terminalProtocol.terminal.reset()
        self.transport.loseConnection()


class SSHAvatar(ConchUser):
    """
    An instance of this class is created after authentication to connect the
    user to the application protocol the underlying service provides.

    The crux of this is accomplished by connecting the ends of an application
    protocol instance (:py:class:`app_proto.SSHApplicationProtocol`) and 
    the underlying SSH session protocol.
    """
    implements(ISession)
    reactor = None

    def __init__(self, user_id):
        ConchUser.__init__(self)
        self.user_id = user_id
        self.avatar_id = uuid.uuid4().hex
        self.channelLookup.update({'session': SSHSession})
        self.terminal = None
        self.term_size = (80, 24)
        self.ssh_protocol = None

    def openShell(self, protocol):
        serverProto = ServerProtocol2(
            make_terminal_adapter, self.reactor, self.user_id)
        serverProto.makeConnection(protocol)
        protocol.makeConnection(wrapProtocol(serverProto))
        self.ssh_protocol = serverProto
        self.set_term_adapter_term_size()
        app_protocol = serverProto.terminalProtocol.app_protocol
        app_protocol.term_size = self.term_size
        app_protocol.update_display()

    def set_term_adapter_term_size(self):
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.term_size = self.term_size 

    def getPty(self, terminal, windowSize, attrs):
        h, w, x, y = windowSize
        self.term_size = (w, h)
        self.terminal = terminal
        return None

    def execCommand(self, protocol, cmd):
        raise NotImplementedError("Not implemented.")

    def  windowChanged(self, newWindowSize):
        h, w, x, y = newWindowSize
        self.term_size = (w, h)
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.term_size = self.term_size
        app_protocol = term_protocol.app_protocol
        app_protocol.term_size = self.term_size
        app_protocol.update_display()

    def closed(self):
        pass

    def shut_down(self):
        """
        Part of avatar interface.
        Shuts down the client attached to this avatar, then
        closes this avatar.
        A new avatar will be attached to the application
        at the same state.
        """
        shut_down_avatar(self)


class SSHRealm(object):
    implements(IRealm)
    reactor = None
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            avatar = SSHAvatar(avatarId)
            avatar.reactor = self.reactor
            entry = users.register_user(avatarId)
            if entry.avatar is not None:
                shut_down_avatar(entry.avatar)
            entry.avatar = avatar
            return (IConchUser, avatar, lambda: None)
        else:
            raise Exception("No supported interfaces found.")


def shut_down_avatar(avatar, msg="Another avatar has logged in for this user.  Logging off ..."):
    avatar.ssh_protocol.clearOnExit = False
    terminalProtocol = avatar.ssh_protocol.terminalProtocol
    if terminalProtocol is None:
        return
    terminal = terminalProtocol.terminal
    terminal.reset()
    terminal.write(msg)
    terminal.loseConnection()

