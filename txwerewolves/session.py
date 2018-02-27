
from __future__ import absolute_import, division, print_function
import collections
import random
import attr
from txwerewolves import users

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
    settings = attr.attrib(default=None)


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
    entry.chat_buf = collections.deque([], 50)
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
    
def send_signal_to_members(session_id, signal, include_invited=False, exclude=None):
    """
    Send `signal` to the session members.
    The signal will be propagated by member avatars
    to their applications.
    """
    session_entry = get_entry(session_id)
    members = set(session_entry.members)
    if include_invited:
        fltr = lambda x: x.invited_id == session_id
        invited_ids = [x.user_id for x in users.generate_user_entries(fltr)]
        members = members.union(invited_ids)
    if not exclude is None:
        exclude_set = set(exclude)
        members = members - exclude_set
    for member in members:
        entry = users.get_user_entry(member)
        avatar = entry.avatar
        avatar.send_app_signal(signal)


