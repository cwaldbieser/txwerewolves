
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
from zope.interface.declarations import implementer


class ServerProtocol2(ServerProtocol):
    """
    Like `tx.conch.insults.insults.ServerProtocol`, but with options.
    """
    clearOnExit = True

    def loseConnection(self):
        if self.clearOnExit:
            self.terminalProtocol.terminal.reset()
        self.transport.loseConnection()


@implementer(ISession)
class SSHAvatar(ConchUser):
    """
    An instance of this class is created after authentication to connect the
    user to the application protocol the underlying service provides.

    The crux of this is accomplished by connecting the ends of an application
    protocol instance (:py:class:`app_proto.SSHApplicationProtocol`) and 
    the underlying SSH session protocol.
    """
    reactor = None

    @classmethod
    def make_instance(klass, user_id, reactor):
        instance = klass()
        instance.user_id = user_id
        instance.reactor = reactor
        instance.channelLookup.update({b'session': SSHSession})
        instance.terminal = None
        instance.term_size = (80, 24)
        instance.ssh_protocol = None
        return instance

    def closed(self):
        pass

    def execCommand(self, protocol, cmd):
        raise NotImplementedError("Not implemented.")

    def getPty(self, terminal, windowSize, attrs):
        h, w, x, y = windowSize
        self.term_size = (w, h)
        self.terminal = terminal
        return None

    def install_application(self, app_protocol):
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.install_application(app_protocol) 

    def init_app_protocol(self):
        """
        Avatar interface
        Initialize default application.
        """
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.init_app_protocol()

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

    def send_app_signal(self, signal):
        """
        Avatar interface.
        Send a signal to the application protocol.
        """
        app_protocol = self.ssh_protocol.terminalProtocol.app_protocol
        app_protocol.receive_signal(signal) 

    def send_message(self, msg):
        """
        Avatar interface.
        Display a message to the client connecting to
        this avatar.
        """
        term_protocol = self.ssh_protocol.terminalProtocol
        app_protocol = term_protocol.app_protocol
        app_protocol.output.append(msg)
        app_protocol.update_display()

    def set_term_adapter_term_size(self):
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.term_size = self.term_size 

    def shut_down(self):
        """
        Part of avatar interface.
        Shuts down the client attached to this avatar, then
        closes this avatar.
        A new avatar will be attached to the application
        at the same state.
        """
        shut_down_avatar(self)

    def  windowChanged(self, newWindowSize):
        h, w, x, y = newWindowSize
        self.term_size = (w, h)
        term_protocol = self.ssh_protocol.terminalProtocol
        term_protocol.term_size = self.term_size
        app_protocol = term_protocol.app_protocol
        app_protocol.term_size = self.term_size
        app_protocol.update_display()


@implementer(IRealm)
class SSHRealm(object):
    reactor = None
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        avatarId = avatarId.decode('utf-8')
        if IConchUser in interfaces:
            entry = users.register_user(avatarId)
            if entry.avatar is not None:
                entry.avatar.shut_down()
            avatar = SSHAvatar.make_instance(avatarId, self.reactor)
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

