"""
Internal domain models for repository-aware AI chat (Phase 9).
Decoupled from database ORM models and external API schemas.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChatQuestion:
    """Represents a validated question submitted to repository chat."""
    owner: str
    repo: str
    question: str
    branch: Optional[str] = None
    top_k: Optional[int] = None

    @property
    def repository_identifier(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


@dataclass
class ChatSource:
    """
    Represents an evidence source chunk supporting an AI answer.
    Must be backed by an actual retrieved chunk from the repository.
    """
    path: str
    chunk_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    category: str = "source"
    score: Optional[float] = None
    retrieval_reason: Optional[str] = None


@dataclass
class ChatAnswer:
    """Structured response from the repository chat service."""
    answer: str
    sources: List[ChatSource] = field(default_factory=list)
    retrieval_mode: str = "vector"
    retrieved_chunks_count: int = 0
    uncertainties: List[str] = field(default_factory=list)
