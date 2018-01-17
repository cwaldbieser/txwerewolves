
import attr


_user_registry = {}

@attr.attrs
class UserRegistryEntry(object):
    user_id = attr.attrib()
    avatar = attr.attrib(default=None)
    app_protocol = attr.attrib(default=None)
    invited_id = attr.attrib(default=None)
    joined_id = attr.attrib(default=None)

def get_user_ids():
    """
    Return all registered user IDs.
    """
    global _user_registry
    users = _user_registry.keys()
    users.sort()
    return users

def register_user(user_id):
    """
    Register a user record.
    """
    global _user_registry
    entry =  _user_registry.get(user_id, None)
    if entry is not None:
        return entry
    entry = UserRegistryEntry(user_id)
    _user_registry[user_id] = entry
    return entry

def get_user_entry(user_id):
    """
    Get a registered user entry.
    Return None if entry does not exist.
    """
    global _user_registry
    return _user_registry.get(user_id, None)

