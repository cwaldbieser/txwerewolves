
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
            user_id = info.user_id
            if not user_id is None:
                return user_id
            # User ID in request?
            args = request.args
            name = args.get("name", [None])[0]
            if not name is None:
                info.user_id = name
                return name
        return defer.fail(UnauthorizedLogin())
                

@implementer(IWebUser)
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

    def init_app_protocol(self):
        user_id = self.user_id
        user_entry = users.get_user_entry(user_id)
        user_entry.avatar = self
        app_protocol = user_entry.app_protocol
        if app_protocol is None:
            app_protocol = lobby.WebLobbyProtocol.make_instance(
                self.reactor,
                user_id,
                self)
            user_entry.app_protocol = app_protocol
        app_protocol = user_entry.app_protocol
        app_protocol.reactor = self.reactor
        app_protocol.parent = weakref.ref(self)  

    def connect_event_source(self, event_source):
        """
        Connect a long connected request from avatar to the
        client so that Server Sent Events (SSEs) can be sent
        to it in `text/event-stream` format.
        """
        event_source.setHeader('content-type', 'text/event-stream')
        self._event_source = event_source
        log.msg("Connected event source to avatar.")
        event_buffer = self._event_buffer
        while len(event_buffer) > 0:
            event = event_buffer.pop()
            self.send_event_to_client(event)

    def send_event_to_client(self, data):
        """
        Send `data` to a client browser.  `data` should be a string.
        """
        event_source = self._event_source
        log.msg("send_event_to_client(): event_source: {}".format(event_source))
        if event_source is None:
            self._event_buffer.appendleft(data)
            return
        for line in data.split('\n'):
            event_source.write('data: ' + line + '\r\n')
            log.msg("Wrote event: {}".format(line))
        event_source.write('\r\n')
        log.msg("Wrote event end.")

    def shut_down(self):
        """
        Part of avatar interface.
        Shuts down the client attached to this avatar, then
        closes this avatar.
        A new avatar will be attached to the application
        at the same state.
        """
        o = {'command': 'shut-down'}
        msg = json.dumps(o)
        self.send_event_to_client(msg) 

    def request_update_from_app(self, key):
        """
        Part of Avatar interface.
        Request a client update of a particular kind from the application.
        """
        self.application.request_update(key)

    def handle_input(self, command):
        """
        Part of Avatar interface.
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
            entry = users.register_user(avatarId)
            avatar = entry.avatar
            if avatar is not None:
                avatar.shut_down()
            avatar = WebAvatar.make_instance(avatarId, self.reactor)
            entry.avatar = avatar
            return (IWebUser, avatar, lambda: None)
        else:
            raise Exception("No supported interfaces found.")


class ISessionInfo(Interface):
    pass


@implementer(ISessionInfo)
class SessionInfo(object):
    user_id = None
    
    def __init__(self, session):
        self.user_id = None

