
.. _web-service:

===============
The Web Service
===============

The web service for the game is provided by
:py:class:`txwerewolves.webservice.WebService`.  The service setup is similar
to the basic setup for :ref:`terminal-service`.  The service entry point is
:py:meth:`txwerewolves.webservice.WebService.startService`.  A web site is 
created and a `Twisted endpoint <https://twistedmatrix.com/documents/current/core/howto/endpoints.html>`_
is constructed from string description of the host, port, and connection options.  The
endpoint is made to listen for incoming network events.  It is configured to use
the web site instance to create a protocol that will communicate with the web
client.

------------
The Web Site
------------

The web site is created using the `Klein <https://klein.readthedocs.io/en/latest/>`_
micro-framework.  While the web client allows anyone to log in with a self
asserted username, it still uses the
`Twisted Cred <https://twistedmatrix.com/documents/current/core/howto/cred.html>`_
system to "authenticate" players.  Before constructing the web site, a
:py:class:`txwerewolves.webauth.WebRealm` is created.  A portal is created and
initialized with the realm.  An instance of 
:py:class:`txwerewolves.webauth.WerewolfWebCredChecker` is registered as the
credential checker for the service.

An instance of :py:class:`txwerewolves.webservice.WebResources` is created and
will serve as a model for the resources in the web site.  The root resources
is obtained from this instance, and a
:py:class:`twisted.web.server.Site` is initialized with this root resource.
The site will act as factory that creates protocol instances that interact with
incoming HTTP requests.

---------
Resources
---------

HTTP requests are routed to resources in the web application.  The resources
have the following meanings:

* **/login** - If the client browser has not established a session, it will be
  redirected to this resource.  Here, a player may choose and submit a login
  name to establish a session.
* **/logout** - A client that accesses this resource will have its session
  expired.
* **/static/** - Static resources like JavaScript, stylesheets, etc. are served
  from this resource tree.
* **/action** - Clients can POST the action a player chooses to this resource
  to send commands to the application.
* **/settings** - Clients can POST settings to this resource to change
  application settings and reset the application.
* **/chat** - Clients can POST chat messages to this resource that will be
  displayed in community chat dialogs.
* **/werewolves** - This resource serves the static HTML for the Werewolves!
  game.
* **/werewolves/...** - There 6 distinct sub-resources a client can request:
  *actions*, *phase-info*, *player-info*, *game-info*, *output*, and *request-all*.
  Requesting one of these resources will trigger a corresponding update
  to be sent via a `Server Sent Event <https://en.wikipedia.org/wiki/Server-sent_events>`_
  (see the */subscribe* resource, below).
* **/lobby** - This resource serves the static HTML for the Lobby application.
* **/lobby/...** - There are 2 sub-resources, *status* and *actions*.
  Requesting one of of these resources will trigger a corresponding update to
  be sent via a `Server Sent Event <https://en.wikipedia.org/wiki/Server-sent_events>`_
  (see the */subscribe* resource, below).
* **/subscribe** - Clients can request this resource to subscribe to
  `server sent events <https://en.wikipedia.org/wiki/Server-sent_events>`_
  from the application.  These events are received by JavaScript handlers in
  the client browser that can update the user interface with new information
  or actions to be selected.


