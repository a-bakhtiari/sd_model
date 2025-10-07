from __future__ import annotations

from typing import List, Optional

try:
    # Prefer Pydantic v2/v1 without deprecated validators
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - fallback if pydantic is not installed
    # Minimal fallback shim so the module can import; runtime validation will be skipped.
    class BaseModel:  # type: ignore
        def dict(self, *args, **kwargs):
            return self.__dict__

    def Field(default=None, **kwargs):  # type: ignore
        return default


class ExpectedConnection(BaseModel):
    """A theoretically expected causal link."""

    from_var: str = Field(..., description="Source variable name")
    to_var: str = Field(..., description="Target variable name")
    relationship: str = Field(..., description="Type of relation, e.g., positive/negative")


class Theory(BaseModel):
    """A theory definition linking expected connections with a bibliographic key."""

    theory_name: str = Field(..., description="Human-readable theory name")
    citation_key: str = Field(..., description="BibTeX citation key")
    expected_connections: List[ExpectedConnection] = Field(
        default_factory=list, description="List of expected causal links"
    )


class FeedbackItem(BaseModel):
    """An actionable feedback item provided by a user or reviewer."""

    feedback_id: str = Field(..., description="Stable ID for referencing the feedback")
    source: str = Field(..., description="Who/where the feedback came from")
    comment: str = Field(..., description="The feedback content")
    action: str = Field(..., description="Suggested action to take")
