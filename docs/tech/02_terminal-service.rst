====================
The Terminal Service
====================

The terminal service is implemented by the class :py:class:`txwerewolves.service.SSHService`.
The service is initialized by the :py:meth:`txwerewolves.service.SSHService.startService`
method which overrides :py:meth:`twisted.application.service.startService`.
A number of components need to be created to start and configure this service.
Because this service uses SSH private-key / public-key authentication, the secret
and public materials for the service must be read in from the file system.  An
instance of :py:class:`twisted.conch.ssh.factory.SSHFactory` is created and
configured with the key material.  The factory will be responsible for creating
an SSH protocol instance when a client connects to the service.  We'll see how
this is configured later on when the endpoint for the service is created.

Because the service is authenticated, the `Twisted Cred <https://twistedmatrix.com/documents/current/core/howto/cred.html>`_
framework is used to provide authentication services.  This means the service
will require a portal, a realm, and at least one credential checker.  The portal
is a simple instance of :py:class:`twisted.cred.portal.Portal`.  The realm is
an instance of :py:class:`txwerewolves.auth.SSHRealm`.  The portal is
initialized with this realm.

The final component need for the authentication system is a credential checker.
Fortunately, Twisted provides :py:class:`twisted.conch.checkers.SSHPublicKeyChecker`.
This checker needs to be initialized with a public key database.  The game uses
:py:class:`twisted.conch.checkers.InMemorySSHKeyDB` to fill this need.  The
keys are read in from a simple JSON file of usernames and their public keys and
stored in the database.  The credential checker is contructed from the key
database and it is registered with the portal.  The portal is assigned to a
property of the :py:class:`~twisted.conch.ssh.factory.SSHFactory` instance.

Finally, a `Twisted endpoint <https://twistedmatrix.com/documents/current/core/howto/endpoints.html>`_
is constructed from a string description and instructed to listen and use the
factory to produce a protocol that will communicate with the connected client.
Once a connection is made, the :py:class:`~twisted.conch.ssh.factory.SSHFactory`
creates an instance of :py:class:`twisted.conch.ssh.transport.SSHServerTransport`
to communicate with the connected client.

-----------------------------
The Terminal Realm and Avatar
-----------------------------

When a client connects to the terminal service and successfully authenticates
with the registered credential checker, the resulting avatar ID is passed to 
the :py:class:`~txwerewolves.auth.SSHRealm` instance that the portal was
initialized with.  The :py:class:`~twisted.conch.ssh.transport.SSHServerTransport`
also requests the :py:class:`twisted.conch.interfaces.IConchUser` interface [#f1]_, and
it expects the realm to return an avatar that supports this interface.

The :py:class:`~txwerewolves.auth.SSHRealm` instance takes the avatar ID and
registers it as in the game's user database using
:py:func:`txwerewolves.users.register_user`.  If a current avatar exists for the
user, it is shut down and a new :py:class:`txwerewolves.auth.SSHAvatar` is created
to replace it.  The active avatar for the user is stored in the user database
as a property of the user entry.

The new avatar is a subclass of :py:class:`twisted.conch.avatar.ConchUser`, so
it inherits much of the code required to communicate with a client terminal.
Namely, it's :py:meth:`~twisted.conch.avatar.ConchUser.openShell` method will be
called when the client requests a shell.  The avatar will use a slightly modified
:py:class:`twisted.conch.insults.insults.ServerProtcol` instance to connect
a :py:class:`txwerewolves.term.TerminalAdapterProtocol` to the SSH protocol
connected to the client terminal.  The 
:py:class:`~txwerewolves.term.TerminalAdapterProtocol` is a subclass of
:py:class:`twisted.conch.insults.insults.TerminalProtocol` so basic curses-style
abstractions are available to the application code.

The terminal avatar delegates many of its functions to its terminal adapter.
Initially, the avatar installs the default terminal application as a property
of the user entry in the user database.  The terminal adapter is also responsible
for translating user input from the client into events that can be handled by the
application protocol.

.. [#f1] Actually, this is rather simplified.
   :py:class:`~twisted.conch.ssh.transport.SSHServerTransport` actually calls on
   :py:class:`twisted.conch.ssh.userauth.SSHUserAuthServer` to perform the user
   authentication.

