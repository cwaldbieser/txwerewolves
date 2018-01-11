
from __future__ import (
    absolute_import,
    print_function,
)
from txsshsvr.app_proto import makeSSHApplicationProtocol
from twisted.cred.portal import IRealm
from twisted.conch.avatar import ConchUser
from twisted.conch.insults.insults import ServerProtocol
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh.session import SSHSession, wrapProtocol
from zope.interface import implements


class SSHAvatar(ConchUser):
    implements(ISession)
    protocolFactory = makeSSHApplicationProtocol

    def __init__(self, avatarId):
        assert self.protocolFactory is not None, "`protocolFactory` is None!"
        ConchUser.__init__(self)
        self.avatarId = avatarId
        self.channelLookup.update({'session': SSHSession})

    def openShell(self, protocol):
        serverProto = ServerProtocol(self.protocolFactory, self)
        serverProto.makeConnection(protocol)
        protocol.makeConnection(wrapProtocol(serverProto))

    def getPty(self, terminal, windowSize, attrs):
        return None

    def execCommand(self, protocol, cmd):
        raise NotImplementedError("Not implemented.")

    def closed(self):
        pass


class SSHRealm(object):
    implements(IRealm)
    
    avatarFactory = SSHAvatar

    def __init__(self):
        assert self.avatarFactory is not None, "`avatarFactory` is None!"

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            return (IConchUser, self.avatarFactory(avatarId), lambda: None)
        else:
            raise Exception("No supported interfaces found.")

