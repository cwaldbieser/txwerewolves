
from __future__ import (
    absolute_import,
    print_function
)
import argparse
import sys
from txwerewolves.service import SSHService
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
        (
            'endpoint', 
            'e', 
            None, 
            "Endpoint string for SSH admin interface.  E.g. 'tcp:2022'"
        ),    
    ]



class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    description = "Werewolves!"
    tapname = "werewolves"
    options = Options
    ssh_endpoint_str = "tcp:2022"

    def makeService(self, options):
        """
        Construct a server from a factory.
        """
        sshService = SSHService()
        sshService.endpointStr = options.get('endpoint', self.ssh_endpoint_str)
        return sshService


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.
serviceMaker = MyServiceMaker()
