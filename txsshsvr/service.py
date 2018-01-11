
# Create SSH keypair with:
# $ ckeygen -t rsa -f ssh-keys/ssh_host_rsa_key

from __future__ import (
    absolute_import,
    print_function,
)
import json
from txsshsvr import auth
from twisted.application.service import Service
from twisted.cred.portal import Portal
from twisted.conch.checkers import (
    SSHPublicKeyChecker,
    InMemorySSHKeyDB)
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.internet import endpoints, reactor


class SSHService(Service):
    reactor = reactor
    realm = auth.SSHRealm()
    endpointStr = 'tcp:2022'
    servicePrivateKey = 'ssh-keys/ssh_host_rsa_key'
    servicePublicKey = 'ssh-keys/ssh_host_rsa_key.pub'
    key_db_path = 'users/user_keys.json'

    def startService(self):
        assert self.realm is not None, "`realm` must not be None!"
        with open(self.servicePrivateKey) as privateBlobFile:
            privateBlob = privateBlobFile.read()
            privateKey = Key.fromString(data=privateBlob)
        with open(self.servicePublicKey) as publicBlobFile:
            publicBlob = publicBlobFile.read()
            publicKey = Key.fromString(data=publicBlob)
        factory = SSHFactory()
        factory.privateKeys = {'ssh-rsa': privateKey}
        factory.publicKeys = {'ssh-rsa': publicKey}
        sshRealm = self.realm
        sshPortal = Portal(sshRealm)
        factory.portal = sshPortal
        with open(self.key_db_path, "r") as f:
            raw_key_map = json.load(f)
        l = []
        for avatar_id, keys in raw_key_map.items():
            key_objects = [Key.fromString(k) for k in keys]
            l.append((avatar_id, key_objects))
        key_map = dict(l)
        keydb = InMemorySSHKeyDB(key_map)
        factory.portal.registerChecker(SSHPublicKeyChecker(keydb))
        ep = endpoints.serverFromString(self.reactor, self.endpointStr)
        d = ep.listen(factory)
        self.port_info_ = []
        d.addCallback(self.onListen)

    def onListen(self, port):
        self.port_info_.append(port)
            
    def stopService(self):
        for port in self.port_info_:
            port.stopListening()

