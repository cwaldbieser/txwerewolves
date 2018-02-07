
import random
import attr

_session_registry = {}
_SESSION_TAGS = [
    'green',
    'blue',
    'red',
    'yellow',
    'orange',
    'white',
    'black',
    'pink',
    'purple',
]


@attr.attrs
class SessionRegistryInfo(object):
    session_id = attr.attrib()
    members = attr.attrib(default=attr.Factory(set))
    owner = attr.attrib(default=None)
    appstate = attr.attrib(default=None)
    chat_buf = attr.attrib(default=None)
    chat_buf_size = attr.attrib(default=50)


def create_session():
    """
    Create a new session.
    """
    global _session_registry
    global _SESSION_TAGS
    entry = None
    for n in range(20):
        tag = random.choice(_SESSION_TAGS)
        num = random.randint(0, 999)
        session_id = "{}-{}".format(tag, num)
        if session_id not in _session_registry:
            entry = SessionRegistryInfo(session_id)
            break
    if entry is None:
        raise Exception("Could not create session ID.")
    _session_registry[session_id] = entry
    entry.chat_buf = []
    entry.chat_buf_size = 50
    return entry

def get_entry(session_id):
    """
    Retrieve session entry.
    """
    global _session_registry
    entry = _session_registry.get(session_id, None)
    return entry
    
def destroy_entry(session_id):
    """
    Remove a session entry.
    """
    global _session_registry
    if session_id in _session_registry:
        del _session_registry[session_id]
    

