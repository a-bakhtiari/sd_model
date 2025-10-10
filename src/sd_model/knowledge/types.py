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
    citations: List[str] = Field(default_factory=list, description="Citation keys supporting this connection")
    page_numbers: Optional[List[str]] = Field(default=None, description="Optional page references")


class Theory(BaseModel):
    """A theory definition linking expected connections with a bibliographic key."""

    theory_name: str = Field(..., description="Human-readable theory name")
    citation_key: str = Field(..., description="BibTeX citation key")
    expected_connections: List[ExpectedConnection] = Field(
        default_factory=list, description="List of expected causal links"
    )
    description: Optional[str] = Field(default="", description="Theory description")
    focus_area: Optional[str] = Field(default="", description="Theory focus area")


class VerifiedCitation(BaseModel):
    """A citation that has been verified via Semantic Scholar."""

    citation_key: str = Field(..., description="BibTeX citation key")
    verified: bool = Field(..., description="Whether the paper was found in Semantic Scholar")
    paper_id: Optional[str] = Field(default=None, description="Semantic Scholar paper ID")
    title: Optional[str] = Field(default=None, description="Paper title")
    authors: Optional[List[str]] = Field(default_factory=list, description="Author names")
    year: Optional[int] = Field(default=None, description="Publication year")
    citation_count: Optional[int] = Field(default=None, description="Number of citations")
    url: Optional[str] = Field(default=None, description="Semantic Scholar URL")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    verified_at: Optional[str] = Field(default=None, description="Verification timestamp")


class PaperSuggestion(BaseModel):
    """A paper suggested by Semantic Scholar for a connection or loop."""

    paper_id: str = Field(..., description="Semantic Scholar paper ID")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(..., description="Author names")
    year: Optional[int] = Field(..., description="Publication year")
    citation_count: int = Field(..., description="Number of citations")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    url: str = Field(..., description="Semantic Scholar URL")
    suggested_for: str = Field(..., description="What this paper is suggested for: 'connection', 'loop', or 'variable'")
    target: str = Field(..., description="The specific target (e.g., 'Reputation → User Base')")


class FeedbackItem(BaseModel):
    """An actionable feedback item provided by a user or reviewer."""

    feedback_id: str = Field(..., description="Stable ID for referencing the feedback")
    source: str = Field(..., description="Who/where the feedback came from")
    comment: str = Field(..., description="The feedback content")
    action: str = Field(..., description="Suggested action to take")
