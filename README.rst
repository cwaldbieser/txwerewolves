===========
Werewolves!
===========

Werewolves! is a party game sometimes called "Mafia".  There are many variations.
This game is based in part on a card game adaption.

The players are randomly assigned roles of either villagers or werewolves.  3 additional
roles are dealt to the table.
At night, some of the villagers with special roles and all the werewolves wake up at different
times and perform certain actions.  After all the night phases are done, the players
may discuss what happend during the night, though they may not actually show each other
their cards.  A player may say the role she received, but she may also claim that she
were dealt a role that she did not receive.

After the discussion, all the players vote for a player to eliminate.  If there is a
player or players who received more than 1 vote, the player(s) with the most votes
are eliminated and the actual roles the players now posess are revealed.  If a
werewolf was killed, the village team wins, even if an innocent villager was eliminated,
too.  The villagers may also win if no one is eliminated and all the werewolves are in
the middle of the table.

Some roles have specialized winning conditions (e.g. the tanner).

------------------------------------
Install, Configure, and Run the Game
------------------------------------

The service supports ssh clients.  To set up the SSH service you need to create a randomly
generated SSH key pair:

.. code:: shell

    $ mkdir ssh-keys
    $ ckeygen -t rsa -f ssh-keys/ssh_host_rsa_key

To configure authentication for the SSH service, edit `users/user_keys.json`.

.. code:: json

    {
        "user1": [
            "pubkey ...",
            "another pubkey ..."
        ],
        "user2": [ "only one pubkey ..." ],
        "user3": [ "etc ..." ]
    }

To start the service:

.. code:: shell

    $ cd /path/to/project
    $ export PYTHONPATH=.
    $ twistd -n werewolves -e tcp:2022


To connect a client to the service:

.. code:: shell

    $ ssh user1@localhost -p 2022

----------------
Playing the Game
----------------

When you first log into the service, you will be in the lobby.  The menus will
allow you to start a session or join a session that another player has started.

A player who creates a session must choose to start a session.  Once a session
starts, all joined players are placed in a game while any pending invitations
are revoked.

In the game, the menus and status areas will guide you through the game.  The
player information area (upper left quadrant) shows your player name and the
role you were randomly dealt.  This information is only available to you.

The game information area (upper right quadrant) shows all the roles that will
be used in this game.  The session owner can adjust these settings and reset
the game.  This information is available to all players throughout the game.
Note that there are always 3 more roles than there are players.  These roles
are dealt to the "table".  Players will not know for certain which roles are
actually held by the other players in the game and which are "on the table."

The phase information area (lower left quadrant) tells you information about
the current phase of the game.  It will provide brief instructions for the
phase and prompt you advance to the next phase.  All players must indicate they
are ready to advance before the phase actually advances.  Until then, a status
indicator will note that the game is waiting on other players.  The information
in this area is mostly the same for all players, though additional information
may be provided to specific roles.

The role power / voting area allows specific roles to exercise their powers
during the appropriate night phases.  During the Daybreak phase, all players
will be allowed to vote for a single player to eliminate.  If any player
achieves more than a single vote, then the player or players with the most
votes is eliminated.

At the end of the game, post game results are displayed in the 2 lower panes.
Who voted to eliminated whom, who was eliminated, who was dealt what role, and
what role each player actually ended up with is revealed to all players.
The winning team is also announced.

++++++++++++++++
The Chat Feature
++++++++++++++++

Players may chat with each other during the game using a community chat window
that may be displayed or dismissed by pressing TAB.  It is against the spirit
of the rules to discuss your actual role until the Daybreak phase.  Once the
Daybreak phase has been reached, the chat feature is an important way to try
to figure out what happened during the night phases.  Players may adopt 
strategies of telling half-truths or outright fibs in order to ferret out the
truth of what really happened.

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

----------
Web Client
----------

You can also play the game using a web browser rather than your terminal.
Authentication is essentially on the honor system in this case.  The web
client has a somewhat modified layout, but gameplay is essentially the same.

You can move back and forth between a terminal client and web client, or web
client to web client, or terminal client to terminal client.  Logging into a
new client will log you out of any previous client where you are logged in as
a particular user.
  
