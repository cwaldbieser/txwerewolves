
from __future__ import (
    absolute_import,
    print_function
)
import argparse
import os.path
import sys
from txwerewolves.service import SSHService
from txwerewolves.webservice import WebService
from twisted.application.service import (
    IServiceMaker, 
    MultiService,
)
import twisted.internet
from twisted.plugin import (
    IPlugin,
)
from twisted.python import usage
from zope.interface.declarations import implementer


class Options(usage.Options):
    optFlags = [
        ('no-ssh', None, 'Disable the SSH service.'),
        ('no-web', None, 'Disable the web service.'),
    ]

    optParameters = [
        (
            'endpoint', 
            's', 
            'tcp:2022', 
            "Endpoint string for SSH interface.  E.g. 'tcp:2022'"
        ),    
        (
            'web-endpoint', 
            'w', 
            'tcp:8080', 
            "Endpoint string for web interface.  E.g. 'tcp:8080'"
        ),    
        (
            'ssh-key-dir',
            'k',
            None,
            "The folder that contains the private and public keys for the SSH service."
        ),
        (
            'user-db',
            'u',
            None,
            "The path to the user database file."
        )
    ]

    def postOptions(self):
        if self['no-ssh'] and self['no-web']:
            raise usage.UsageError("No services enabled.  Quitting.")


@implementer(IServiceMaker, IPlugin)
class MyServiceMaker(object):
    description = "Werewolves!"
    tapname = "werewolves"
    options = Options
    ssh_endpoint_str = "tcp:2022"
    web_endpoint_str = "tcp:8080"

    def makeService(self, options):
        """
        Construct a server from a factory.
        """
        no_ssh = options.get('no-ssh', False)
        no_web = options.get('no-web', False)
        reactor = twisted.internet.reactor
        root_service = MultiService()
        if not no_ssh:
            ssh_key_dir = options.get('ssh-key-dir', None)
            private_key_path, pubkey_path = self._get_ssh_service_keys(ssh_key_dir)
            user_db = options.get('user-db', None)
            if user_db is None:
                user_db = self._get_user_db()
            ssh_service = SSHService()
            ssh_service.endpoint_str = options.get('endpoint', self.ssh_endpoint_str)
            ssh_service.servicePrivateKey = private_key_path
            ssh_service.servicePublicKey = pubkey_path
            ssh_service.key_db_path = user_db
            ssh_service.setServiceParent(root_service)
        if not no_web:
            web_service = WebService.make_instance(reactor)
            web_service.endpoint_str = options.get('web-endpoint', self.web_endpoint_str)
            web_service.setServiceParent(root_service)
        return root_service

    def _get_user_db(self):
        """
        Return the path to the SSH service user database (JSON file).
        """
        user_path = os.path.expanduser("~/.txwerewolvesrc/users/user_keys.json")
        system_path = "/etc/txwerewolves/users/user_keys.json"
        for pth in [user_path, system_path]:
            if os.path.isfile(pth):
                return pth
        raise Exception("Could not find SSH service user database file, `user_keys.json`.")

    def _get_ssh_service_keys(self, key_dir):
        """
        Return the paths to the private and public keys for the SSH service.
        """
        private_path = None
        public_path = None
        user_dir = os.path.expanduser("~/.txwerewolvesrc/ssh_keys")
        system_dir = "/etc/txwerewolves/ssh_keys"
        if key_dir is not None:
            search_dirs = [key_dir]
        else:
            search_dirs = []
        search_dirs.extend([user_dir, system_dir])
        for dirname in search_dirs:
            key_path = os.path.join(dirname, 'ssh_host_rsa_key')
            if private_path is None and os.path.isfile(key_path):
                private_path = key_path
            key_path = os.path.join(dirname, 'ssh_host_rsa_key.pub')
            if public_path is None and os.path.isfile(key_path):
                public_path = key_path
        if private_path is None:
            raise Exception("Could not find private key file ('ssh_host_rsa_key') for SSH service.")
        if public_path is None:
            raise Exception("Could not find public key file ('ssh_host_rsa_key.pub') for SSH service.")
        return private_path, public_path 
            

# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.
serviceMaker = MyServiceMaker()
