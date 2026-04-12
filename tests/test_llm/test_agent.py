"""Tests for bimkg.llm.agent (LangGraph agent).

Unit tests verify tool wrapping and prompt construction.
Integration tests require ANTHROPIC_API_KEY and are skipped in CI.
"""

from __future__ import annotations

import os

import pytest

from bimkg.llm.agent import ALL_TOOLS, create_bim_agent
from bimkg.llm.prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES


class TestPrompts:
    def test_system_prompt_has_schema(self) -> None:
        assert "bim_objects" in SYSTEM_PROMPT
        assert "ADJACENT_TO" in SYSTEM_PROMPT
        assert "PipingComponent" in SYSTEM_PROMPT

    def test_few_shot_examples_count(self) -> None:
        assert len(FEW_SHOT_EXAMPLES) == 5

    def test_few_shot_all_have_required_keys(self) -> None:
        for ex in FEW_SHOT_EXAMPLES:
            assert "question" in ex
            assert "tool" in ex
            assert "query" in ex
            assert "answer" in ex


class TestTools:
    def test_all_tools_count(self) -> None:
        assert len(ALL_TOOLS) == 5

    def test_tool_names(self) -> None:
        names = {t.name for t in ALL_TOOLS}
        assert names == {"sql_query", "text_search", "sparql_query", "cypher_query", "kpi_summary"}

    def test_tools_have_descriptions(self) -> None:
        for t in ALL_TOOLS:
            assert len(t.description) > 20


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
    reason="No LLM API key set (ANTHROPIC_API_KEY or GOOGLE_API_KEY)"
)
class TestAgentE2E:
    """End-to-end tests with real API. Run manually with API key set."""

    @pytest.fixture(scope="class")
    def agent(self):
        if os.environ.get("GOOGLE_API_KEY"):
            return create_bim_agent(model="gemini-2.5-flash", provider="google")
        return create_bim_agent(provider="anthropic")

    def test_pipeline_count(self, agent) -> None:
        from bimkg.llm.agent import ask
        answer = ask("P-10147 파이프라인에 몇 개의 객체가 있어?", agent)
        assert "129" in answer or "P-10147" in answer

    def test_plant_summary(self, agent) -> None:
        from bimkg.llm.agent import ask
        answer = ask("이 플랜트의 전체 객체 수와 총 중량을 알려줘", agent)
        assert "12,009" in answer or "12009" in answer or "12,009" in answer
