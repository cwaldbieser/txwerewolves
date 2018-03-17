
.. _users:

=====
Users
=====

-----------------
The User Database
-----------------

The user database is a mapping of user entries that have been registered in the
service, either via the :ref:`terminal service <terminal-service>` or via the
:ref:`web service <web-service>`.  Each player is identifier by a unique
avatar ID which maps to a corresponding user entry.

------------
User Entries
------------

A user entry contains the avatar ID of the player.  It also contains a reference
to the current avatar for the player and a reference to the current application.
The entry also has some basic state information concerning whether a player has
been invited to or has joined a session.


