from __future__ import annotations


class KnowledgeError(RuntimeError):
    pass


class KnowledgeNotFoundError(KnowledgeError):
    pass


class KnowledgeConflictError(KnowledgeError):
    pass

