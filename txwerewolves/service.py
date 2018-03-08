
# Create SSH keypair with:
# $ ckeygen -t rsa -f ssh-keys/ssh_host_rsa_key

from __future__ import (
    absolute_import,
    print_function,
)
import json
from txwerewolves import auth
from twisted.application.service import Service
from twisted.cred.portal import Portal
from twisted.conch.checkers import (
    SSHPublicKeyChecker,
    InMemorySSHKeyDB)
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.internet import endpoints, reactor
from twisted.python import log


class SSHService(Service):
    reactor = reactor
    realmFactory = auth.SSHRealm
    endpoint_str = 'tcp:2022'
    servicePrivateKey = 'ssh-keys/ssh_host_rsa_key'
    servicePublicKey = 'ssh-keys/ssh_host_rsa_key.pub'
    key_db_path = 'users/user_keys.json'

    def startService(self):
        """
        This is the main entry point into the service when it
        starts.  Multiple components need to be created and
        assembled to create the final service.  It helps to
        look at the process in reverse.

        An endpoint (`ep`) is created that listens on a port.  When a
        connection is received, it uses a protocol `factory` to create
        a new SSH protocol instance.

        The factory is configure with a portal that will be used to
        authenticate users and create avatars for them at the service.

        The factory portal registered a :py:class:`SSHPublicKeychecker`
        instance so that users can authenticate using SSH public/private
        key pairs.  The allowed public keys and the matching users are
        configured in a JSON file that the service reads on start up.

        The protocol factory (:py:class:`twisted.conch.ssh.factory.SSHFactory`)
        is indirectly responsible for calling the `login` method on its portal.
        When the "ssh-userauth" service of the SSH protocol is requested, the
        factory creates an instance of 
        :py:class:`twisted.conch.ssh.userauth.SSHUserAuthServer` to create a
        public key credential and pass it to the portal's `login` method.  It
        is at this point the public key checker can authenticate the credential.

        The portal was also configured with `self.realmFactory` which happens
        to produce an instance of :py:class:`auth.SSHRealm`.  This realm creates 
        an avatar instance which will represent the user on the service side of
        the connection.

        The avatar created will be an instance of :py:class:`auth.SSHAvatar`.
        This avatar is responsible for connecting the user to the service
        application logic.
        """
        assert self.realmFactory is not None, "`realmFactory` must not be None!"
        with open(self.servicePrivateKey, "r") as privateBlobFile:
            privateBlob = privateBlobFile.read()
            privateKey = Key.fromString(data=privateBlob)
        with open(self.servicePublicKey, "r") as publicBlobFile:
            publicBlob = publicBlobFile.read()
            publicKey = Key.fromString(data=publicBlob)
        factory = SSHFactory()
        factory.privateKeys = {b'ssh-rsa': privateKey}
        factory.publicKeys = {b'ssh-rsa': publicKey}
        sshRealm = self.realmFactory()
        sshRealm.reactor = self.reactor
        sshPortal = Portal(sshRealm)
        factory.portal = sshPortal
        with open(self.key_db_path, "r") as f:
            raw_key_map = json.load(f)
        l = []
        for avatar_id, keys in raw_key_map.items():
            key_objects = [Key.fromString(k.encode('utf-8')) for k in keys]
            l.append((avatar_id.encode('utf-8'), key_objects))
        key_map = dict(l)
        keydb = InMemorySSHKeyDB(key_map)
        factory.portal.registerChecker(SSHPublicKeyChecker(keydb))
        ep = endpoints.serverFromString(self.reactor, self.endpoint_str)
        d = ep.listen(factory)
        self.port_info_ = []
        d.addCallback(self.onListen)

    def onListen(self, port):
        self.port_info_.append(port)
            
    def stopService(self):
        for port in self.port_info_:
            port.stopListening()

