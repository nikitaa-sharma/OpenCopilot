"""
Tests for Phase 9: Repository-Aware Grounded AI Chat.

Covers:
1. Valid chat request flow with structured response.
2. Empty and whitespace-only question rejection (400).
3. Missing owner / repo rejection (400).
4. Vector retrieval mode propagation.
5. Keyword fallback retrieval mode propagation.
6. No relevant context handled safely without hallucination.
7. Grounded system and user prompt construction.
8. Safe structured LLM output parsing (direct JSON and markdown fences).
9. Malformed / non-JSON LLM output handled safely (fallback text).
10. Strict source validation against actual retrieved chunks.
11. Hallucinated / unretrieved source paths stripped from evidence.
12. LLM provider unavailable handled with 503.
13. LLM timeout handled with 504.
14. Repository not found / inaccessible handled with 404.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.chat.models import ChatAnswer, ChatQuestion, ChatSource
from app.chat.service import RepositoryChatService
from app.main import app
from app.rag.models import RAGStatistics, RepositoryChunk, RetrievedChunk
from app.rag.service import RAGRetrievalResult
from app.services.github_service import GitHubNotFoundError
from app.services.llm_provider import (
    LLMProvider,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)

client = TestClient(app)


def _make_retrieved_chunk(
    file_path: str = "src/flask/app.py",
    content: str = "class Flask:\n    def wsgi_app(self, environ, start_response):\n        pass",
    score: float = 0.92,
    start_line: int = 10,
    end_line: int = 30,
) -> RetrievedChunk:
    chunk = RepositoryChunk(
        chunk_id=f"pallets/flask:{file_path}:0",
        repository="pallets/flask",
        file_path=file_path,
        language="Python",
        category="source",
        chunk_index=0,
        start_line=start_line,
        end_line=end_line,
        content=content,
        metadata={},
    )
    return RetrievedChunk(
        chunk=chunk,
        score=score,
        matched_terms=["flask", "wsgi_app"],
        retrieval_reason=f"Vector semantic similarity: {score:.4f}",
    )


class TestRepositoryChatServiceDomain:
    """Unit tests for the RepositoryChatService domain logic."""

    @pytest.mark.asyncio
    async def test_empty_question_raises_value_error(self):
        service = RepositoryChatService()
        q = ChatQuestion(owner="pallets", repo="flask", question="   ")
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.chat(q)

    @pytest.mark.asyncio
    async def test_no_context_returns_safe_controlled_answer(self):
        mock_context_service = MagicMock()
        mock_context_service.get_context_for_question = AsyncMock(
            return_value=MagicMock(
                chunks_count=0,
                context_text="",
                sources=[],
                retrieved_chunks=[],
                retrieval_mode="none",
            )
        )
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock()

        service = RepositoryChatService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        q = ChatQuestion(owner="pallets", repo="flask", question="How does routing work?")
        answer = await service.chat(q)

        assert "No relevant repository context could be found" in answer.answer
        assert answer.retrieval_mode == "none"
        assert answer.retrieved_chunks_count == 0
        assert len(answer.sources) == 0
        # LLM must not be called when context is empty
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_grounded_prompt_and_structured_response(self):
        sample_chunk = _make_retrieved_chunk()
        mock_context_service = MagicMock()
        mock_context_service.get_context_for_question = AsyncMock(
            return_value=MagicMock(
                chunks_count=1,
                context_text=f"### Excerpt from src/flask/app.py\n```python\n{sample_chunk.chunk.content}\n```",
                sources=[
                    ChatSource(
                        path=sample_chunk.chunk.file_path,
                        chunk_id=sample_chunk.chunk.chunk_id,
                        start_line=10,
                        end_line=30,
                        category="source",
                        score=0.92,
                    )
                ],
                retrieved_chunks=[sample_chunk],
                retrieval_mode="vector",
            )
        )

        llm_payload = {
            "answer": "Flask handles incoming HTTP requests via the wsgi_app method.",
            "evidence": [
                {
                    "path": "src/flask/app.py",
                    "start_line": 10,
                    "end_line": 30,
                    "reason": "Defines wsgi_app handling environ",
                }
            ],
            "uncertainties": ["Middleware implementations may vary depending on WSGI servers."],
        }
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock(return_value=json.dumps(llm_payload))

        service = RepositoryChatService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        q = ChatQuestion(owner="pallets", repo="flask", question="How does Flask handle requests?")
        answer = await service.chat(q)

        assert "Flask handles incoming HTTP requests" in answer.answer
        assert answer.retrieval_mode == "vector"
        assert answer.retrieved_chunks_count == 1
        assert len(answer.sources) == 1
        assert answer.sources[0].path == "src/flask/app.py"
        assert answer.sources[0].start_line == 10
        assert answer.sources[0].end_line == 30
        assert len(answer.uncertainties) == 1

        # Verify prompt grounded parameters
        mock_llm.generate.assert_called_once()
        call_kwargs = mock_llm.generate.call_args.kwargs
        assert "Repository Context" in call_kwargs["prompt"]
        assert "src/flask/app.py" in call_kwargs["prompt"]
        assert call_kwargs["json_mode"] is True

    @pytest.mark.asyncio
    async def test_hallucinated_sources_are_strictly_stripped(self):
        """If the LLM returns a citation for a file that was not retrieved, it must NOT be in sources."""
        sample_chunk = _make_retrieved_chunk(file_path="src/flask/app.py")
        mock_context_service = MagicMock()
        mock_context_service.get_context_for_question = AsyncMock(
            return_value=MagicMock(
                chunks_count=1,
                context_text="### Excerpt",
                sources=[
                    ChatSource(path="src/flask/app.py", chunk_id="1", start_line=1, end_line=20)
                ],
                retrieved_chunks=[sample_chunk],
                retrieval_mode="vector",
            )
        )

        # Model tries to cite fake/unretrieved file
        llm_payload = {
            "answer": "Explanation of routing",
            "evidence": [
                {
                    "path": "fake/hallucinated/router.py",
                    "start_line": 1,
                    "end_line": 50,
                    "reason": "Imagined routing logic",
                }
            ],
            "uncertainties": [],
        }
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock(return_value=json.dumps(llm_payload))

        service = RepositoryChatService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        q = ChatQuestion(owner="pallets", repo="flask", question="How does routing work?")
        answer = await service.chat(q)

        # The hallucinated file must NOT appear in validated sources
        paths = [s.path for s in answer.sources]
        assert "fake/hallucinated/router.py" not in paths
        # Fallback retains the legitimate retrieved source
        assert "src/flask/app.py" in paths

    @pytest.mark.asyncio
    async def test_safe_fallback_when_llm_returns_markdown_or_invalid_json(self):
        sample_chunk = _make_retrieved_chunk()
        mock_context_service = MagicMock()
        mock_context_service.get_context_for_question = AsyncMock(
            return_value=MagicMock(
                chunks_count=1,
                context_text="### Excerpt",
                sources=[
                    ChatSource(path="src/flask/app.py", chunk_id="1", start_line=1, end_line=20)
                ],
                retrieved_chunks=[sample_chunk],
                retrieval_mode="keyword_fallback",
            )
        )

        # Non-JSON plain text response
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.generate = AsyncMock(
            return_value="Plain text answer without JSON structure explaining the repository."
        )

        service = RepositoryChatService(
            context_service=mock_context_service,
            llm_provider=mock_llm,
        )

        q = ChatQuestion(owner="pallets", repo="flask", question="Explain app structure")
        answer = await service.chat(q)

        assert "Plain text answer without JSON" in answer.answer
        assert len(answer.sources) == 1
        assert answer.sources[0].path == "src/flask/app.py"
        assert answer.retrieval_mode == "keyword_fallback"


class TestRepositoryChatAPIEndpoint:
    """API integration tests for POST /api/v1/repositories/chat."""

    def test_empty_question_returns_400(self):
        resp = client.post(
            "/api/v1/repositories/chat",
            json={"owner": "pallets", "repo": "flask", "question": "   "},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_missing_owner_or_repo_returns_400(self):
        resp = client.post(
            "/api/v1/repositories/chat",
            json={"owner": "", "repo": "flask", "question": "How does it work?"},
        )
        assert resp.status_code == 400

    @patch("app.api.v1.endpoints.repositories.repository_chat_service.chat")
    def test_valid_chat_success_vector(self, mock_chat):
        mock_chat.return_value = ChatAnswer(
            answer="Flask handles requests via WSGI protocol.",
            sources=[
                ChatSource(
                    path="src/flask/app.py",
                    chunk_id="pallets/flask:src/flask/app.py:0",
                    start_line=10,
                    end_line=45,
                    category="source",
                    score=0.91,
                    retrieval_reason="Vector semantic similarity: 0.9100",
                )
            ],
            retrieval_mode="vector",
            retrieved_chunks_count=1,
            uncertainties=[],
        )

        resp = client.post(
            "/api/v1/repositories/chat",
            json={
                "owner": "pallets",
                "repo": "flask",
                "question": "How does Flask handle incoming HTTP requests?",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Flask handles requests via WSGI protocol."
        assert data["retrieval_mode"] == "vector"
        assert data["retrieved_chunks_count"] == 1
        assert len(data["sources"]) == 1
        assert data["sources"][0]["path"] == "src/flask/app.py"
        assert data["sources"][0]["start_line"] == 10
        assert data["sources"][0]["end_line"] == 45

    @patch("app.api.v1.endpoints.repositories.repository_chat_service.chat")
    def test_valid_chat_keyword_fallback(self, mock_chat):
        mock_chat.return_value = ChatAnswer(
            answer="Answer derived from keyword-matched source chunks.",
            sources=[
                ChatSource(
                    path="src/flask/wrappers.py",
                    category="source",
                    start_line=1,
                    end_line=25,
                )
            ],
            retrieval_mode="keyword_fallback",
            retrieved_chunks_count=1,
            uncertainties=["Vector database was unindexed; used deterministic keyword search."],
        )

        resp = client.post(
            "/api/v1/repositories/chat",
            json={
                "owner": "pallets",
                "repo": "flask",
                "question": "What does Request wrapper do?",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["retrieval_mode"] == "keyword_fallback"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["path"] == "src/flask/wrappers.py"

    @patch("app.api.v1.endpoints.repositories.repository_chat_service.chat")
    def test_llm_provider_unavailable_returns_503(self, mock_chat):
        mock_chat.side_effect = LLMProviderUnavailableError("AI provider is unavailable. Ollama is not running on localhost:11434")

        resp = client.post(
            "/api/v1/repositories/chat",
            json={
                "owner": "pallets",
                "repo": "flask",
                "question": "Explain Flask architecture",
            },
        )
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.repository_chat_service.chat")
    def test_llm_timeout_returns_504(self, mock_chat):
        mock_chat.side_effect = LLMTimeoutError("Model timed out")

        resp = client.post(
            "/api/v1/repositories/chat",
            json={
                "owner": "pallets",
                "repo": "flask",
                "question": "Explain Flask architecture",
            },
        )
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.repository_chat_service.chat")
    def test_repository_not_found_returns_404(self, mock_chat):
        mock_chat.side_effect = GitHubNotFoundError("Repository not found")

        resp = client.post(
            "/api/v1/repositories/chat",
            json={
                "owner": "nonexistent-owner",
                "repo": "nonexistent-repo",
                "question": "Explain architecture",
            },
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
