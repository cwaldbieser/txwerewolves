
import string

class TodoProtocol(object):
    parent = None
    terminal = None
    user_id = None
    _key_id = None
    def handle_input(self, key_id, modifier):
        self._key_id = key_id
        self.update_display()

    def update_display(self):
        terminal = self.terminal
        terminal.reset()
        key_id = self._key_id
        if key_id is None or not key_id in string.printable:
            terminal.write("Dum de dum ...")
        else:
            terminal.write("You typed '{}'.".format(key_id))
            self._key_id = None

