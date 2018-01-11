
from __future__ import print_function
import argparse
import sys
from txsshsvr.service import SSHService
from twisted.application.service import (
    IServiceMaker, 
    MultiService,
)
from twisted.plugin import (
    IPlugin,
)
from twisted.python import usage
from zope.interface import implements


class Options(usage.Options):
    optParameters = [
        ["config", "c", None, 
            "Options in a specific configuration override options in any other "
            "configurations."],
        ['ssh-endpoint', 's', None, 
            "Endpoint string for SSH admin interface.  E.g. 'tcp:2022'"],    
        ['admin-group', 'a', None, 
            "Administrative access group.  Default 'txgroupadmins'"],    
        ['ssh-private-key', 'k', None, 
            "SSH admin private key.  Default 'keys/id_rsa'."],    
        ['ssh-public-key', 'p', None, 
            "SSH admin public key.  Default 'keys/id_rsa.pub'."],    
        ['web-endpoint', 'w', None, 
            "Endpoint string for web service."],    
    ]


class TwistdOpts(usage.Options):
    optFlags = [
        ["syslog", None, "Log to syslog."],
    ]
    optParameters = [
        ['logfile', 'l', "Log to file.", None],
        ['prefix', None, "Prefix when logging to syslog (default 'twisted').", "twisted"],    
    ]
    def parseArgs(self, *args):
        pass


class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    description = "SSH Service"
    tapname = "sshsrv"
    options = TwistdOpts
    ssh_endpoint_str = "tcp:2022"

    def makeService(self, options):
        """
        Construct a server from a factory.
        """
        # Parse the original `twistd` command line for logging options.
        #parser = argparse.ArgumentParser("twistd argument parser")
        #parser.add_argument(
        #    '--syslog',
        #    action='store_true')
        #args, unknown = parser.parse_known_args()
        sshService = SSHService()
        #sshService.endpointStr = self.ssh_endpoint_str
        #sshService.servicePrivateKey = ssh_private_key
        #sshService.servicePublicKey = ssh_public_key
        return sshService


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.
serviceMaker = MyServiceMaker()
