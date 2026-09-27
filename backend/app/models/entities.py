"""
Database entity models planned for OpenSource Copilot.
These schemas outline the relational structure for PostgreSQL storage.
Actual table creation migrations will occur when PostgreSQL integration is activated.
"""

from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.config import settings
from app.models.base import Base


class User(Base):
    """
    Persistent user account for OpenSource Copilot (Phase 12).
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    developer_profile: Mapped[Optional["DeveloperProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    user_repositories: Mapped[List["UserRepository"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    skills: Mapped[List["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        back_populates="user"
    )


class DeveloperProfile(Base):
    """
    Persistent developer skill profile for an authenticated user (Phase 12).
    Connects Phase 10 DeveloperSkillProfile to PostgreSQL storage.
    """
    __tablename__ = "developer_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    programming_languages: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    frameworks: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    tools: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    domains: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    experience_level: Mapped[str] = mapped_column(String(50), default="beginner", nullable=False)
    interests: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped["User"] = relationship(back_populates="developer_profile")


class UserRepository(Base):
    """
    Repository analyzed or saved by an authenticated user (Phase 12).
    Tracks user exploration history without altering public repository visibility.
    """
    __tablename__ = "user_repositories"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    repository_url: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="user_repositories")


class UserSkill(Base):
    """Technical skill associated with a developer profile."""
    __tablename__ = "user_skills"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)  # e.g., "TypeScript", "Python", "Docker"
    proficiency_level: Mapped[str] = mapped_column(String(50), default="intermediate")  # beginner, intermediate, advanced

    user: Mapped["User"] = relationship(back_populates="skills")


class Repository(Base):
    """Analyzed GitHub repository metadata."""
    __tablename__ = "repositories"

    owner: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    full_name: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    stars_count: Mapped[int] = mapped_column(Integer, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    primary_language: Mapped[Optional[str]] = mapped_column(String(100))
    architecture_summary: Mapped[Optional[str]] = mapped_column(Text)

    files: Mapped[List["RepositoryFile"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    issues: Mapped[List["Issue"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(back_populates="repository")


class RepositoryFile(Base):
    """Indexed file in repository for RAG context."""
    __tablename__ = "repository_files"

    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(1000), index=True)
    extension: Mapped[Optional[str]] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[Optional[str]] = mapped_column(String(100))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    sha: Mapped[Optional[str]] = mapped_column(String(100))
    content: Mapped[Optional[str]] = mapped_column(Text)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    embeddings: Mapped[List["Embedding"]] = relationship(back_populates="file", cascade="all, delete-orphan")



class Issue(Base):
    """Fetched GitHub issue."""
    __tablename__ = "issues"

    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    github_issue_id: Mapped[int] = mapped_column(Integer, index=True)
    issue_number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[Optional[str]] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(50), default="open")  # open, closed
    labels: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    repository: Mapped["Repository"] = relationship(back_populates="issues")
    analysis: Mapped[Optional["IssueAnalysis"]] = relationship(back_populates="issue", uselist=False)
    contribution_guide: Mapped[Optional["ContributionGuide"]] = relationship(back_populates="issue", uselist=False)


class IssueAnalysis(Base):
    """AI-generated analysis of an issue."""
    __tablename__ = "issue_analyses"

    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), unique=True, index=True)
    difficulty_score: Mapped[str] = mapped_column(String(50))  # easy, medium, hard
    required_skills: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text)
    affected_components: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    issue: Mapped["Issue"] = relationship(back_populates="analysis")


class ContributionGuide(Base):
    """Tailored contribution path for an issue."""
    __tablename__ = "contribution_guides"

    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), unique=True, index=True)
    steps: Mapped[dict] = mapped_column(JSON, default=list)
    recommended_files: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    testing_tips: Mapped[Optional[str]] = mapped_column(Text)

    issue: Mapped["Issue"] = relationship(back_populates="contribution_guide")


class ChatSession(Base):
    """Conversation thread scoped to a repository."""
    __tablename__ = "chat_sessions"

    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Repository Q&A")

    repository: Mapped["Repository"] = relationship(back_populates="chat_sessions")
    user: Mapped[Optional["User"]] = relationship(back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Message within a repository chat session."""
    __tablename__ = "chat_messages"

    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    context_sources: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class Embedding(Base):
    """Vector representation of repository file chunks (planned pgvector integration)."""
    __tablename__ = "embeddings"

    file_id: Mapped[int] = mapped_column(ForeignKey("repository_files.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_content: Mapped[str] = mapped_column(Text)
    # Note: pgvector column Vector(dim) will be activated when pgvector is loaded in migrations
    embedding_model: Mapped[str] = mapped_column(String(100))

    file: Mapped["RepositoryFile"] = relationship(back_populates="embeddings")


try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType, TypeEngine, Float

    class Vector(UserDefinedType):  # type: ignore[no-redef]
        def __init__(self, dim: int = 384):
            super().__init__()
            self.dim = dim

        def get_col_spec(self, **kw: Any) -> str:
            return f"vector({self.dim})"

        class Comparator(TypeEngine.Comparator):
            def cosine_distance(self, other: Any) -> Any:
                return self.op("<=>", return_type=Float)(other)

            def l2_distance(self, other: Any) -> Any:
                return self.op("<->", return_type=Float)(other)

            def max_inner_product(self, other: Any) -> Any:
                return self.op("<#>", return_type=Float)(other)

            def l1_distance(self, other: Any) -> Any:
                return self.op("<+>", return_type=Float)(other)

        comparator_factory = Comparator


class RepositoryChunk(Base):
    """
    Persistent representation of a repository chunk with vector embedding.
    Stored in PostgreSQL with the pgvector extension for semantic search (Phase 8).
    """
    __tablename__ = "repository_chunks"

    repository_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    repository_identifier: Mapped[str] = mapped_column(
        String(300), index=True
    )  # e.g., "pallets/flask" or "pallets/flask:main"
    file_path: Mapped[str] = mapped_column(String(1000), index=True)
    language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    embedding: Mapped[Optional[Any]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )

    repository: Mapped[Optional["Repository"]] = relationship()
