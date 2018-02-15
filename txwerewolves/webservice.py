
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import json
import textwrap
from txwerewolves import users
from txwerewolves import webauth
from klein import Klein
from six.moves import urllib
from twisted.application.service import Service
from twisted.cred.portal import Portal
from twisted.internet.endpoints import serverFromString
from twisted.python.components import registerAdapter
from twisted.python import log
from twisted.web.server import (
    Session,
    Site,
)
import werkzeug

def prefix_resource(request, path="", params="", query="", fragment=""):
    """
    Construct a URL using the site prefix and the resource parts.
    """
    uri = request.uri
    log.msg("uri: {}".format(uri))
    p = urllib.parse.urlparse(uri)
    p2 = (p.scheme, p.netloc, path, params, query, fragment)
    url = urllib.parse.urlunparse(p2)
    return url


def webauthn(f):

    def _authn(self, request, *args, **kwds):
        info = webauth.ISessionInfo(request.getSession())
        if info.user_id is None:
            request.redirect("/login")
        else:
            return f(self, request, *args, **kwds)

    return _authn


class WebResources(object):
    app = Klein()
    reactor = None
    portal = None

    @classmethod
    def make_instance(klass, reactor, portal):
        instance = klass()
        instance.reactor = reactor
        instance.portal = portal
        return instance

    @app.route('/')
    def home(self, request):
        request.redirect(prefix_resource(request, path="/lobby"))

    @app.route('/lobby')
    @webauthn
    def lobby(self, request):
        return "The Lobby"

    @app.route('/login', methods=['GET', 'POST'])
    def login(self, request):
        log.msg("Method: {}".format(request.method))
        if request.method == 'GET':
            return self._get_login(request)
        elif request.method == 'POST':
            return self._post_login(request)

    def _get_login(self, request):
        log.msg("request: {}".format(request.__class__))
        return textwrap.dedent("""\
        <html>
        <head><title>Login</title></head>
        <body>
            <form method="POST" action="/login">
                <label for="user_id">User ID:</label>
                <input id="user_id" name="name" type="text" maxchars="20">
                <br>
                <button type="submit">Submit</button>
            </form>
        </bodY>
        </html>
        """)

    def _post_login(self, request):
        portal = self.portal
        web_req_cred = webauth.WebRequestCredential(request)
        d = portal.login(web_req_cred, None, webauth.IWebUser)
        d.addCallback(self._handle_login_success, request)
        d.addErrback(self._handle_login_fail, request)
        return d

    def _handle_login_success(self, result, request):
        log.msg("Handle login success.")
        interface, avatar, logout = result
        user_id = avatar.user_id
        info = webauth.ISessionInfo(request.getSession())
        info.user_id = user_id
        request.redirect("/")

    def _handle_login_fail(self, failure, request):
        log.msg("Handle failure: {}".format(failure))
        request.redirect("/login")

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
    session_length = 60 * 30

    @classmethod
    def make_instance(klass, reactor):
        instance = klass()
        klass.reactor = reactor
        return instance

    def make_web_service(self):
        """
        Create and return the web service site.
        """
        web_realm = webauth.WebRealm.make_instance(self.reactor)
        portal = Portal(web_realm)
        checker = webauth.WerewolfWebCredChecker.make_instance()
        portal.registerChecker(checker)
        resources = WebResources.make_instance(
            self.reactor,
            portal)
        root = resources.app.resource()
        site = Site(root)
        session_length = self.session_length

        def sessionFactory(site, uid, reactor=None):
            s = Session(site, uid, reactor=reactor)
            s.sessionTimeout = session_length
            return s

        site.sessionFactory = sessionFactory
        site.displayTracebacks = self.displayTracebacks
        return site

    def startService(self):
        site = self.make_web_service()
        registerAdapter(webauth.SessionInfo, Session, webauth.ISessionInfo)
        ep = serverFromString(self.reactor, self.endpoint_str)
        d = ep.listen(site)
        d.addCallback(self.setListeningPort)

    def stopService(self):
        port = self._port
        if port is not None:
            port.stopListening()

    def setListeningPort(self, port):
        self._port = port


