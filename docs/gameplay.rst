
================
Playing the Game
================

---------------
Client Behavior
---------------

The game can be played using a terminal client or a web client.  A player may
switch freely between clients, but only one will remain open for a given user
ID at any one time.  If a player logs into the service with another client
(web or terminal), the previous client is automatically disconnected from the
service.

It is possible to disconnect from the service without quitting the game.  The
CTRL-D key combination in the terminal client will do this.  There is no such
explicit command for the web client, but the player can simply close her browser
and later log in with a new client to resume where she left off.

---------
The Lobby
---------

When you first log into the service, you will be in the lobby.  The menus will
allow you to start a session or join a session that another player has started.

A player who creates a session may choose to start a session.  Once a session
starts, all players who accepted invitations to the session are placed into a 
game while any pending invitations are revoked.

--------------------
The Werewolves! Game
--------------------

During gameplay, the menus and status areas will guide you through the game.  The
player information area shows your player name and the role you were randomly
assigned.  This information is only available to you.

The game information area shows all the roles that will be used in this game.
The session owner can adjust these settings and restart the game with the new
settings.  

.. warning::

    Changing settings will restart a game in progress!

General game information is available to all players throughout the game.
Note that there are always 3 more roles than there are players.  These roles
are assigned to the "table".  Players will not know for certain which roles are
actually held by the other players in the game and which are "on the table."

The phase information area tells you information about the current phase of the
game.  It will provide a brief overview of the phase and prompt you advance to
the next phase.  All players must indicate they are ready to advance before the
game will advance to the next phase.  Until then, a status indicator will note
that the game is waiting on other players.  The information in this area is
mostly the same for all players, though additional information may be provided
to specific roles.

The role power area allows specific roles to exercise their powers during the
appropriate night phases.  During the Daybreak phase, all players will be
allowed to vote for a single player to eliminate.  If any player receives more
than a single vote, then the player or players with the most votes is
eliminated.

At the end of the game, post game results are displayed.  Who voted to eliminate
whom, who was eliminated, who was dealt what role, and
what role each player actually ended up with are revealed to all players.
The winning team is also announced.

----------------
The Chat Feature
----------------

Players may chat with each other in the lobby and during the *Werewolves!* game
using a community chat window.

It is against the spirit of the rules to discuss your actual role until the
Daybreak phase.  Once the Daybreak phase has been reached, the chat feature is
an important way to try to figure out what happened during the night phases,
unless all players are able to communicate freely by other means (e.g. they may
all be playing together in the same room).  

Players may adopt strategies of telling half-truths or outright fibs in order
to ferret out the truth of what really happened.

------------------
Victory Conditions
------------------

The werewolf team wins if at least one player is a werewolf AND no werewolves
were eliminated.

The village team wins if at least 1 werewolf was eliminated OR no one was
eliminated and no player was a werewolf.

The tanner wins only if the player who holds this role at the end of the game
is eliminated.  The village team can win a joint victory with the tanner if
a werewolf is eliminated in addition to the tanner.

The minion wins with the werewolf team, even if the minion is eliminated.
If no players are werewolves but 1 player is the minion, the werewolf team
can still win if a member of the village other than the tanner or the minion
is eliminated.

-----
Roles
-----

* Villager - no special powers, wins with the Village team.
* Seer - Can use her mystic powers to either view 2 of the 3 roles on the table
  or 1 player's role.  Wins with the Village team.
* Robber - May steal a role from another player.  That player gets robber role.
  The robber gets to see his new role.  The player with the robber role at the
  end of the game wins with the Village team.
* Troublemaker - The troublemaker may choose to swap the roles of 2 other
  players *without* looking at them.  The troublemaker wins with the Village
  team.
* Insomniac - The insomniac wakes up at the end of the night and checks to see
  if her role changed.  The player with the insomniac role at the end of the
  game wins with the Village team.
* Werewolf - All the werewolf players wake up together at night and can see
  each other.  A player holding a werewolf role at the end of the game wins
  with the Werewolf team.
* Minion - The minion wakes up after the werewolves and can see who they are.
  The werewolves *cannot* see who the minion is.  The player holding the 
  minion role at the end of the game wins with the Werewolf team.  Note that
  the Werewolf team wins even if the minion is eliminated, such is his
  fanaticism.
* Tanner - The tanner has a profession that has left him longing for the sweet
  embrace of death.  The tanner only wins if he is eliminated.  The Werewolf
  team does *not* win if the tanner is eliminated, because a good deed will
  have been done for this poor soul.  The Village team does not win if the
  tanner is eliminated alone (his blood is on the villager's hands, after all),
  but the village can win a joint victory with the tanner if a werewolf is
  eliminated with him-- the vanquishing of a cursed one allows for some
  collateral casulties.

