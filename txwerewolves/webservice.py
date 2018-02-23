
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import json
import os
import textwrap
from txwerewolves import (
    session,
    users,
    webauth,
)
from klein import Klein
from six.moves import urllib
from twisted.application.service import Service
from twisted.cred.portal import Portal
from twisted.internet import defer
from twisted.internet.endpoints import serverFromString
from twisted.python.components import registerAdapter
from twisted.python import log
from twisted.web.server import (
    Session,
    Site,
)
from twisted.web.static import File
import werkzeug

static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
html_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src/html")

def check_authenticated(request):
    info = webauth.ISessionInfo(request.getSession())
    if info.user_id is None:
        log.msg("Not authorized; redirecting ...")
        request.redirect("/login")
        return False
    else:
        return True

def get_avatar(request):
    """
    Get the user avatar from the request.
    """
    info = webauth.ISessionInfo(request.getSession())
    user_id = info.user_id
    entry = users.get_user_entry(user_id)
    avatar = entry.avatar
    return avatar


class WebResources(object):
    app = Klein()
    reactor = None
    portal = None
    _html_files = None

    @classmethod
    def make_instance(klass, reactor, portal):
        instance = klass()
        instance.reactor = reactor
        instance.portal = portal
        instance._html_files = {}
        html_keys = ['login', 'lobby', 'werewolves']
        for key in html_keys:
            instance._load_html(key)
        return instance

    def _load_html(self, html_key):
        global html_dir
        html_fname = "{}.html".format(html_key)
        path = os.path.join(html_dir, html_fname)
        with open(path, "r") as f:
            page = f.read()
        self._html_files[html_key] = page

    @app.route('/')
    def home(self, request):
        request.redirect("/lobby")

    @app.route('/static/', branch=True)
    def static(self, request):
        global static_path
        log.msg("static_path: {}".format(static_path))
        return File(static_path)

    @app.route('/action', methods=['POST'])
    def action(self, request):
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        avatar.handle_input(int(request.args.get('command')[0]));

    @app.route('/chat', methods=['POST'])
    def chat(self, request):
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        user_id = avatar.user_id
        message = request.args.get('message')[0];
        user_entry = users.get_user_entry(user_id)
        session_id = user_entry.joined_id or user_entry.invited_id
        if session_id is None:
            return
        session_entry = session.get_entry(session_id)
        chat_buf = session_entry.chat_buf
        chat_buf.append((user_id, message))
        signal = ('chat-message', {'sender': user_id}) 
        session.send_signal_to_members(session_id, signal, include_invited=True)

    @app.route('/werewolves')
    def werewolves(self, request):
        if not check_authenticated(request):
            return
        return self._html_files['werewolves']

    @app.route('/werewolves/actions')
    def werewolves_actions(self, request):
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        avatar.request_update_from_app('actions')

    @app.route('/lobby')
    def lobby(self, request):
        if not check_authenticated(request):
            return
        return self._html_files['lobby']

    @app.route('/lobby/status')
    def lobby_status(self, request):
        log.msg("routed to /lobby/status")
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        avatar.request_update_from_app('status')

    @app.route('/lobby/actions')
    def lobby_actions(self, request):
        log.msg("routed to /lobby/actions")
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        avatar.request_update_from_app('actions')

    @app.route('/subscribe')
    def subscribe(self, request):
        log.msg("routed to /subscribe")
        if not check_authenticated(request):
            return
        avatar = get_avatar(request)
        avatar.connect_event_source(request)
        d = defer.Deferred()
        return d

    @app.route('/login', methods=['GET', 'POST'])
    def login(self, request):
        log.msg("Method: {}".format(request.method))
        if request.method == 'GET':
            return self._get_login(request)
        elif request.method == 'POST':
            return self._post_login(request)

    def _get_login(self, request):
        log.msg("request: {}".format(request.__class__))
        return self._html_files['login']

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
        request.redirect("/lobby")

    def _handle_login_fail(self, failure, request):
        log.msg("Handle failure: {}".format(failure))
        request.redirect("/login")

    @app.route("/logout")
    def logout(self, request):
        s = request.getSession()
        s.expire()
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


