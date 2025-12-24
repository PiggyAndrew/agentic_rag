def _set_tracing_context(ctx=None):
    return None

def get_tracing_context():
    return {
        "parent": None,
        "project_name": None,
        "tags": None,
        "metadata": None,
        "enabled": False,
        "client": None,
    }

