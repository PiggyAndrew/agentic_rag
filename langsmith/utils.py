class LangSmithError(Exception):
    pass

def tracing_is_enabled():
    return False

def get_tracer_project():
    return "default"

