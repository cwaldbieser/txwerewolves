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

