"""LangChain/LangGraph agent for BIM natural language queries.

Creates a multi-tool ReAct agent that routes questions to the appropriate
data source (SQL, SPARQL, Cypher, FTS5, KPI) and returns answers
grounded in the BIM knowledge graph.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from bimkg.llm.prompts import SYSTEM_PROMPT
from bimkg.llm import tools as tool_funcs


# ---------------------------------------------------------------------------
# Wrap plain functions as LangChain tools
# ---------------------------------------------------------------------------

@tool
def sql_query(query: str) -> str:
    """Execute a read-only SQL query on the BIM SQLite database (bimkg.db).
    Use for counting, filtering, aggregating objects by class/pipeline/weight/etc.
    Input: a valid SQL SELECT statement."""
    return tool_funcs.sql_query(query)


@tool
def text_search(query: str) -> str:
    """Full-text search on BIM object names, pipeline names, and system paths.
    Use when the user asks to find objects by name pattern.
    Input: search terms (e.g. 'Blind Flange', 'P-10147')."""
    return tool_funcs.text_search(query)


@tool
def sparql_query(query: str) -> str:
    """Execute a SPARQL SELECT query on the OWL ontology graph.
    Use for semantic queries: class membership, property traversal, ontology structure.
    Input: a valid SPARQL SELECT query with PREFIX declarations."""
    return tool_funcs.sparql_query(query)


@tool
def cypher_query(query: str) -> str:
    """Execute a Cypher query on the Neo4j graph database.
    Use for: neighbor traversal, path finding, construction sequence (MUST_PRECEDE),
    pipeline membership, zone analysis.
    Input: a valid Cypher MATCH/RETURN query."""
    return tool_funcs.cypher_query(query)


@tool
def kpi_summary(query: str) -> str:
    """Look up pre-computed KPIs for the plant, a pipeline, or a zone.
    Input: 'plant', 'pipeline P-10147', or 'zone 15'."""
    return tool_funcs.kpi_summary(query)


ALL_TOOLS = [sql_query, text_search, sparql_query, cypher_query, kpi_summary]


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def create_bim_agent(
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.0,
) -> object:
    """Create and return a BIM query agent (LangGraph ReAct).

    Requires ANTHROPIC_API_KEY environment variable.
    """
    llm = ChatAnthropic(model=model, temperature=temperature)

    agent = create_react_agent(
        llm,
        ALL_TOOLS,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )

    return agent


def ask(question: str, agent=None) -> str:
    """Convenience: ask a single question and return the answer string."""
    if agent is None:
        agent = create_bim_agent()
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    # Extract the last AI message
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return str(result)
