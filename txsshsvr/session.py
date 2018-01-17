
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
    return entry



