"""CCGS agent layer.

`agents.registry.json` declares what each agent may do; `agents.runner` is the
deterministic, standard-library-only executor for its task types. LLM reasoning
is performed by the DSH agent session, never by this package.
"""

__all__ = ["runner"]
