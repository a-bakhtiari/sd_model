"""LLM client abstraction.

This module exposes a minimal interface used by some pipeline steps to optionally
call an LLM. It gracefully degrades to a deterministic heuristic when no LLM is
configured.
"""

