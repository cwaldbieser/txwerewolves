
import attr


_user_registry = {}

@attr.attrs
class UserRegistryEntry(object):
    user_id = attr.attrib()
    avatars = attr.attrib(default=attr.Factory(dict))

def add_avatar(user_id, avatar):
    """
    Add an avatar to the user registry.
    """
    global _user_registry
    avatar_id = avatar.avatar_id
    entry = _user_registry.get(user_id, None)
    if entry is None:
        entry = UserRegistryEntry(user_id=user_id)
        _user_registry[user_id] = entry
    entry.avatars[avatar_id] = avatar

def remove_avatar(user_id, avatar):
    """
    Remove an avatar from the user registry.
    """
    global _user_registry
    avatar_id = avatar.avatar_id
    entry = _user_registry.get(user_id, None)
    if entry is None:
        return
    del entry.avatars[avatar_id]
    if len(entry.avatars) == 0:
        del _user_registry[user_id]

def get_user_ids():
    """
    Return all registered user IDs.
    """
    global _user_registry
    users = _user_registry.keys()
    users.sort()
    return users

def get_avatars_for_user(user_id):
    """
    Return all avatars for the user_id.
    """
    global _user_registry
    entry = _user_registry.get(user_id, None)
    if entry:
        return entry.avatars.values() 
    else:
        return []



