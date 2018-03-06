====================================
Install, Configure, and Run the Game
====================================

The service supports both authenticated SSH terminal clients as well as 
unauthenticated browser-based web clients.  A single service supports
both types of clients.

-------------------------
SSH Service Configuration
-------------------------

To set up the SSH service you need to create a randomly
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

-------------------------
Web Service Configuration
-------------------------

The web service doesn't support any advance configuration options at this time.

--------------------
Starting the Service
--------------------

To start the service:

.. code:: shell

    $ cd /path/to/project
    $ export PYTHONPATH=.
    $ twistd -n werewolves -e tcp:2022


To connect an SSH client to the service (assuming a typical OpenSSH command-line client):

.. code:: shell

    $ ssh user1@localhost -p 2022

To connect a web client to the service, simply browse to the IP address of the
interface and the port on which the web service runs.  E.g. http://192.168.0.100:8080/


