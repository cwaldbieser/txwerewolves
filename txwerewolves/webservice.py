
from __future__ import division, print_function
from klein import Klein
from twisted.application.service import Service
from twisted.internet.endpoints import serverFromString
from twisted.python import log
from twisted.web.server import Site
import werkzeug


class WebResources(object):
    app = Klein()
    reactor = None

    @app.route('/')
    def home(self, request):
        return 'Hello, world!'

    @app.handle_errors(werkzeug.exceptions.NotFound)
    def error_handler_404(self, request, failure):
        log.msg("http_status={status}, client_ip={client_ip}, path={path}".format(
            status=404,
            client_ip=request.getClientIP(),
            path=request.path))
        request.setResponseCode(404)
        return '''404 - Not Found'''

    @app.handle_errors
    def error_handler_500(self, request, failure):
        request.setResponseCode(500)
        log.msg("status={status} http_status=500, client_ip={client_ip}: {err}".format(
            status=500,
            client_ip=request.getClientIP(),
            err=str(failure)))
        return '''500 - Internal Error'''


class WebService(Service):
    _port = None
    displayTracebacks = False
    endpoint_str = "tcp:8080"
    reactor = None

    @classmethod
    def make_instance(klass, reactor):
        instance = klass()
        klass.reactor = reactor
        return instance

    def make_web_service(self):
        """
        Create and return the web service site.
        """
        resources = WebResources()
        resources.reactor = self.reactor
        root = resources.app.resource()
        site = Site(root)
        return site

    def startService(self):
        site = self.make_web_service()
        site.displayTracebacks = self.displayTracebacks
        ep = serverFromString(self.reactor, self.endpoint_str)
        d = ep.listen(site)
        d.addCallback(self.setListeningPort)

    def stopService(self):
        port = self._port
        if port is not None:
            port.stopListening()

    def setListeningPort(self, port):
        self._port = port


