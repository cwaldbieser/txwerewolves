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

The service supports ssh clients.  To set up the SSH service you need to create a randomly
generated SSH key pair:

.. code:: shell

    $ mkdir ssh-keys
    $ ckeygen -t rsa -f ssh-keys/ssh_host_rsa_key

To configure authentication for the service, edit `users/user_keys.json`.

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

