
from __future__ import (
    absolute_import,
    division,
    print_function,
)
import collections
import json
import weakref
from txwerewolves import (
    lobby,
    users,
)
from txwerewolves.interfaces import (
    IAvatar,
    IWebApplication,
)
import attr
import six
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import ICredentials
from twisted.cred.portal import IRealm
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer
from twisted.python import log
from zope.interface import (
    implementer,
    Interface,
)


class IWebRequestCredential(ICredentials):
    pass


class IWebUser(Interface):
    pass

 
@implementer(IWebRequestCredential)
@attr.attrs
class WebRequestCredential(object):
    request = attr.attrib()


@implementer(ICredentialsChecker)
class WerewolfWebCredChecker(object):
    credentialInterfaces = [IWebRequestCredential]

    @classmethod
    def make_instance(klass):
        instance = klass()
        return instance 
    
    def requestAvatarId(self, credentials):
        if IWebRequestCredential.providedBy(credentials):
            request = credentials.request
            # User ID in session?
            session = request.getSession()
            info = ISessionInfo(session)
            avatar = info.avatar
            if not avatar is None:
                return avatar.user_id
            # User ID in request?
            args = request.args
            name = args.get(six.b("name"), [None])[0]
            if not name is None:
                return name.decode('utf-8')
        return defer.fail(UnauthorizedLogin())
                

@implementer(IAvatar, IWebUser)
class WebAvatar(object):
    user_id = None
    reactor = None
    _event_buffer = None
    _event_source = None

    @classmethod
    def make_instance(klass, user_id, reactor):
        instance = klass()
        instance.user_id = user_id 
        instance.reactor = reactor
        instance._event_buffer = collections.deque([], 20)
        instance.init_app_protocol()
        return instance

    @property
    def application(self):
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        app_protocol = user_entry.app_protocol
        return app_protocol

    def install_application(self, app_protocol):
        if not IWebApplication.providedBy(app_protocol):
            app_protocol = app_protocol.produce_compatible_application(
                IWebApplication, parent=self)
        entry = users.get_user_entry(self.user_id)
        entry.app_protocol = app_protocol
        data = {'install-app': app_protocol.resource}
        command_str = json.dumps(data)
        self.send_event_to_client(command_str)
        
    def init_app_protocol(self):
        """
        Initialize the default application.
        """
        log.msg("WebAvatar initializing app protocol ...")
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        user_entry.avatar = self
        app_protocol = user_entry.app_protocol
        if app_protocol is None:
            log.msg("User entry has no app protocol-- creating a new one ...")
            app_protocol = lobby.WebLobbyProtocol.make_instance(
                self.reactor,
                user_id,
                self)
        else:
            log.msg("Producing compatible app ...")
            app_protocol = app_protocol.produce_compatible_application(
                IWebApplication, parent=self)
            log.msg("Produced compatible app.")
        user_entry.app_protocol = app_protocol
        app_protocol.reactor = self.reactor
        app_protocol.parent = weakref.ref(self)  

    def connect_event_source(self, event_source):
        """
        Connect a long connected request from avatar to the
        client so that Server Sent Events (SSEs) can be sent
        to it in `text/event-stream` format.
        """
        event_source.setHeader(b'content-type', b'text/event-stream')
        self._event_source = event_source
        log.msg("Connected event source to avatar.")
        event_buffer = self._event_buffer
        while len(event_buffer) > 0:
            event = event_buffer.pop()
            self.send_event_to_client(event)

    def _reset_event_source(self, data=None):
        self._event_source = None
        self._event_buffer = collections.deque([], 20)
        if data is not None:
            self._event_buffer.appendleft(data)

    def send_event_to_client(self, data):
        """
        Send `data` to a client browser.  `data` should be a string.
        """
        log.msg("send_event_to_client()")
        event_source = self._event_source
        if event_source is None:
            log.msg("event_source is None")
            self._event_buffer.appendleft(data)
            return
        log.msg("data: {}".format(data))
        for line in data.split('\n'):
            log.msg("line: {}".format(line))
            try:
                event_source.write(('data: ' + line + '\r\n').encode('utf-8'))
            except Exception as ex:
                log.msg("Oops!  {}".format(ex))
                self._reset_event_source(data=data)
                return
            log.msg("Wrote event: {}".format(line))
        try:
            event_source.write('\r\n'.encode('utf-8'))
        except Exception as ex:
            log.msg("Could not write line end to event source: {}".format(ex))
            self._reset_event_source(data=data)
            return
        log.msg("Wrote event end.")

    def send_app_signal(self, signal):
        """
        Avatar interface.
        Send a signal to the application protocol.
        """
        app_protocol = self.application
        if app_protocol is None:
            log.msg("App protocol is none; cannot send signal to app.")
            return
        app_protocol.receive_signal(signal) 

    def send_message(self, msg):
        """
        Avatar interface.
        Display a message to the client connecting to
        this avatar.
        """
        command = {'output': msg}
        command_str = json.dumps(command)
        self.send_event_to_client(command_str)

    def shut_down(self):
        """
        Part of avatar interface.
        Shuts down the client attached to this avatar, then
        closes this avatar.
        A new avatar will be attached to the application
        at the same state.
        """
        log.msg("Called `shut_down()` for {}".format(self))
        o = {'shut-down': 'new avatar connected'}
        msg = json.dumps(o)
        try:
            self.send_event_to_client(msg) 
        except Exception as ex:
            log.msg("Couldn't send shutdown message to client. {}".format(ex))
        self._event_source = None

    def logoff(self):
        """
        Log off the avatar.
        This destroys both the avatar and the user application state.
        """
        log.msg("Called `logoff()` for {}".format(self))
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        user_entry.avatar = None
        user_entry.app_protocol = None
        user_entry.joined_id = None
        user_entry.invited_id = None

    def request_update_from_app(self, key):
        """
        Request a client update of a particular kind from the application.
        """
        self.application.request_update(key)

    def handle_input(self, command):
        """
        Handle client input. 
        """
        self.application.handle_input(command)

@implementer(IRealm)
class WebRealm(object):
    reactor = None

    @classmethod
    def make_instance(klass, reactor):
        instance = klass()
        instance.reactor = reactor
        return instance

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IWebUser in interfaces:
            log.msg("WebRealm.requestAvatar(): looking up user entry for `{}`.".format(avatarId))
            entry = users.register_user(avatarId)
            log.msg("WebRealm.requestAvatar(): entry: `{}`.".format(entry))
            avatar = entry.avatar
            if avatar is not None:
                log.msg("WebRealm.requestAvatar(): Shutting down existing avatar.")
                avatar.shut_down()
            avatar = WebAvatar.make_instance(avatarId, self.reactor)
            log.msg("WebRealm.requestAvatar(): Created new web avatar.")
            entry.avatar = avatar
            log.msg("WebRealm.requestAvatar(): Assinged new web avatar to entry.")
            return (IWebUser, avatar, lambda: None)
        else:
            raise Exception("No supported interfaces found.")


class ISessionInfo(Interface):
    pass


@implementer(ISessionInfo)
class SessionInfo(object):
    avatar = None
    
    def __init__(self, session):
        self.avatar = None


