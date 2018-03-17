============
Applications
============

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

---------------------
The Lobby Application 
---------------------

The Lobby application is the default application.  Each player's state is
maintained by a finite state machine.  Players may move through various
states.  A player may start a session and invite others to join.  She may
accept an invitation or reject it.  She can leave a session or cancel a
session she initiated.  She may also start a session which players have
joined.  this latter action will replace the Lobby application for players who
have joined the session with the Werewolves! game application.

---------------------------
The Werewolves! Application
---------------------------

The Werewolves! game application is different from the Lobby application in that
the game state is shared amongst the members of the session.  In contrast, the
Lobby application of a given player doesn't share state with the Lobby
applications of other players-- all interaction is mediated via changes to a
shared session instance.

The game application is modeled as a shared finite state machine.  Players are
only able to activate transitions in the game's state machine when their role
becomes active, but this information is generally kept hidden from the other
players.
