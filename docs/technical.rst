=======================
Technical Documentation
=======================

------------
Architecture
------------

The game runs as a single process which is launched via the Twisted command
line program, :program:`twistd`.  The application is written as a `Twisted
Application Plugin <http://twistedmatrix.com/documents/current/core/howto/tap.html>`_.

The main entry point is `serviceplugin.py`, which will be located in the
:file:`twisted/plugins` folder of your source repository or of your Python
environment's :file:`site-packages` folder, depending on whether you have
cloned the repository or have installed the software (e.g. with :program:`pip`).

There is a global name, `serviceMaker` at the end of this script which is bound
to an instance of a class that implements the :class:`twisted.application.service.IServiceMaker`
interface.  When :program:`twistd` runs, it detects this application plugin and
displays its *tapname* attribute as one of its subcommands.  If you run the
`werewolves` sub-command, the :py:meth:`~twisted.application.service.IServiceMaker.makeService`
method is called on this instance.  This is the program entry point.

The :py:meth:`~twisted.application.service.IServiceMaker.makeService` method
parses command line options, looks for configuration files, and generally
configures both the terminal service and the web service provided by the game.
The two services are set as child services of a generic parent 
:py:meth:`~twisted.application.service.MultiService` instance.  The general
Twisted reactor framework will begin to send network events to the services as they become available.

--------------------
The Terminal Service
--------------------

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

"""""""""""""""""""""""""""""
The Terminal Realm and Avatar
"""""""""""""""""""""""""""""

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
 
---------------
The Web Service
---------------

----------------
The Applications
----------------

The user entry for a given player always has a single active application
registered at any given time.  The application must be the appropriate kind for
the current user avatar.  E.g. terminal avatars require terminal applications
and web avatars require web applications.  Applications must be convertible from
one kind to another so that a user can switch between interfaces.  Because of
this, an application should maintain state in its `appstate` property which can
readilly be transferred to a similar application of a different kind.
Applications implement the
:py:meth:`txwerewolves.interfaces.IApplication.produce_compatible_application`
to perform such conversions.

"""""""""""""""""""""
The Lobby Application 
"""""""""""""""""""""

The Lobby application is the default application.  Each player's state is
maintained by a finite state machine.  Players may move through various
states.  A player may start a session and invite others to join.  She may
accept an invitation or reject it.  She can leave a session or cancel a
session she initiated.  She may also start a session which players have
joined.  this latter action will replace the Lobby application for players who
have joined the session with the Werewolves! game application.

"""""""""""""""""""""""""""
The Werewolves! Application
"""""""""""""""""""""""""""

The Werewolves! game application is different from the Lobby application in that
the game state is shared amongst the members of the session.  In contrast, the
Lobby application of a given player doesn't share state with the Lobby
applications of other players-- all interaction is mediated via changes to a
shared session instance.

The game application is modeled as a shared finite state machine.  Players are
only able to activate transitions in the game's state machine when their role
becomes active, but this information is generally kept hidden from the other
players.

.. [#f1] Actually, this is rather simplified.
   :py:class:`~twisted.conch.ssh.transport.SSHServerTransport` actually calls on
   :py:class:`twisted.conch.ssh.userauth.SSHUserAuthServer` to perform the user
   authentication.

