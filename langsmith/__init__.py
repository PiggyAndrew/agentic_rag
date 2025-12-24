class Client:
    def __init__(self, *args, **kwargs):
        pass
    def get_run_url(self, run=None, project_name=None):
        return ""
    def flush(self):
        pass

class RunTree:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.child_runs = getattr(self, "child_runs", [])
        self.inputs = getattr(self, "inputs", {})
        self.outputs = getattr(self, "outputs", {})
        self.extra = getattr(self, "extra", {})
        self.tags = getattr(self, "tags", [])
        self.events = getattr(self, "events", [])
    def dict(self, exclude=None):
        data = self.__dict__.copy()
        if exclude:
            for key in exclude:
                data.pop(key, None)
        return data
    @classmethod
    def construct(cls, **kwargs):
        return cls(**kwargs)

def get_tracing_context():
    return {
        "parent": None,
        "project_name": None,
        "tags": None,
        "metadata": None,
        "enabled": False,
        "client": None,
    }

from .utils import tracing_is_enabled, get_tracer_project, LangSmithError  # noqa: F401
from .run_helpers import _set_tracing_context  # noqa: F401
from . import run_trees  # noqa: F401
