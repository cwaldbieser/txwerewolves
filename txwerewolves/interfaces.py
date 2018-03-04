
from __future__ import (
    absolute_import,
    division,
    print_function,
)
from zope import interface


class IApplication(interface.Interface):

    avatar = interface.Attribute("The avatar used by a client to interact with this application.")
    appstate = interface.Attribute("The state machine that drives the application logic.")
    parent = interface.Attribute("A `weakref.ref` to the parent object.")
    reactor = interface.Attribute("The twisted reactor.")
    user_id = interface.Attribute("The user_id of the avatar.")

    def receive_signal(signal):
        """
        Receive a signal from some other agent in the game.
        """

    def produce_compatible_application(iface, parent):
        """
        Produce an application with state similar to this one, but compatible
        with interface `iface`.
        """


class ITerminalApplication(IApplication):

    dialog = interface.Attribute("If set, a modal dialog object that can display itself to the terminal and handle input.")
    term_size = interface.Attribute("The width and height of the terminal.")
    terminal = interface.Attribute("The application interacts with the client terminal via this object.")

    def handle_input(key_id, modifiers):
        """
        Handles terminal input.
        """

    def install_dialog(dialog):
        """
        Installs a modal terminal dialog.
        """

    def terminalSize(w, h):
        """
        Called when the terminal is resized.
        """

    def update_display():
        """
        Redraw the display on the client terminal.
        """
 

class IWebApplication(IApplication):

    resource = interface.Attribute("The web resource associated with this application.")

    def handle_input(command):
        """
        Parse user input and act on commands.
        """

    def request_update(key):
        """
        Update the client based on the key provided.
        """
 
class IAvatar(interface.Interface):

    user_id = interface.Attribute("The user ID")
    reactor = interface.Attribute("The twisted reactor")
    application = interface.Attribute("The application currently associated with this avatar.")
  
    def install_application(app_protocol):
        """
        Link an application to this avatar and the user entry.
        """

    def init_app_protocol():
        """
        Initialize the default application protocol.
        """

    def send_app_signal(signal):
        """
        Send a signal to the linked application.
        """

    def send_message(msg):
        """
        Display a message via the client connecting to this avatar.
        """

    def shut_down():
        """
        Shut down the client attached to this avatar, then
        close this avatar and remove it from the user entry.
        A new avatar can be attached to the application at the
        same state.
        """  


     
  

