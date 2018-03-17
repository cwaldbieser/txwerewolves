============
Architecture
============

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

