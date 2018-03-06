
from __future__ import (
    absolute_import,
    print_function
)
import argparse
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
from zope.interface import implements


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
    ]

    def postOptions(self):
        if self['no-ssh'] and self['no-web']:
            raise usage.UsageError("No services enabled.  Quitting.")


class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
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
            ssh_service = SSHService()
            ssh_service.endpoint_str = options.get('endpoint', self.ssh_endpoint_str)
            ssh_service.setServiceParent(root_service)
        if not no_web:
            web_service = WebService.make_instance(reactor)
            web_service.endpoint_str = options.get('web-endpoint', self.web_endpoint_str)
            web_service.setServiceParent(root_service)
        return root_service


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.
serviceMaker = MyServiceMaker()
