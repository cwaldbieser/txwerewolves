====================================
Install, Configure, and Run the Game
====================================

The service supports both authenticated SSH terminal clients as well as 
unauthenticated browser-based web clients.  A single service supports
both types of clients.

-----------------------
Installing the Software
-----------------------

"""""""""""""""""""""""""""""""""""""""""""""""
Installing from the Python Package Index (PyPi)
"""""""""""""""""""""""""""""""""""""""""""""""

**txwerewolves** can be installed from the Python Package Index.  Althought not
specifically required, I *strongly* recommend installing into a Python virtual
environment.  I like to use
`virtualenvwrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`_ .

.. code:: shell

    $ mkvirtualenv wolfenv
    (wolfenv)$ pip install txwerewolves

""""""""""""""""""""""""""""""""""
Installing from cloned Github repo
""""""""""""""""""""""""""""""""""

Clone the source repository and install the dependencies via `pip` into a Python
virtualenv.

E.g.

.. code:: shell

    $ git clone https://github.com/cwaldbieser/txwerewolves.git
    $ cd txwerewolves
    $ mkvirtualenv wolfenv
    (wolfenv)$ pip install -r requirements.txt

The last command may fail if certain operating system dependencies are not
satisfied.  Satisfying those dependencies isn't covered here.

-------------------------
SSH Service Configuration
-------------------------

To set up the SSH service you need to create a randomly
generated SSH key pair:

.. code:: shell

    $ mkdir -p ~/.txwerewolvesrc/ssh_keys
    $ ckeygen -t rsa -f ~/.txwerewolvesrc/ssh_keys/ssh_host_rsa_key

To configure authentication for the SSH service, edit `~/.txwerewolvesrc/users/user_keys.json`.

.. code:: json

    {
        "user1": [
            "pubkey ...",
            "another pubkey ..."
        ],
        "user2": [ "only one pubkey ..." ],
        "user3": [ "etc ..." ]
    }

.. note::

    The location of the SSH service keys and user database can be configured
    from the command line.  The service will also check in `$HOME/.txwerewolvesrc`
    and `/etc/txwerewolves` for the sub-directories `users` and `ssh_keys`.

-------------------------
Web Service Configuration
-------------------------

The web service doesn't support any advance configuration options at this time.

--------------------
Starting the Service
--------------------

To start the service:

.. code:: shell

    (wolfenv)$ twistd -n werewolves

When running against a cloned git repo, you need to add the project folder to
your PYTHONPATH.

.. code:: shell

    $ cd /path/to/project
    $ export PYTHONPATH=.
    $ twistd -n werewolves 


To connect an SSH client to the service (assuming a typical OpenSSH command-line client):

.. code:: shell

    $ ssh user1@localhost -p 2022

To connect a web client to the service, simply browse to the IP address of the
interface and the port on which the web service runs.  E.g. http://192.168.0.100:8080/


