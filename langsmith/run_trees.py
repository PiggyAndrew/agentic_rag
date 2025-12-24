from . import Client

_CLIENT = None

def get_cached_client(**init_kwargs):
    return Client(**init_kwargs)

