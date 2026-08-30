from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agents.nodes.compact_node import compact_thread_node
from src.agents.nodes.guardrail_node import input_guardrail_node, output_guardrail_node
from src.agents.nodes.personal_query_router_node import (
    personal_query_router_node,
    save_explicit_personal_memory_node,
)
from src.agents.nodes.planner_node import planner_node
from src.agents.state import AgentState
from src.agents.tools import ALL_TOOLS
from src.config import get_settings

# Tools whose own output is already the final answer - no confirmation needed and no benefit
# from a second LLM pass to "relay" it. Routing straight to END after these avoids that second
# pass, which some models handle poorly (observed: hallucinating a bogus repeat tool-call instead
# of plain text). Calendar/reminder tools still go back through planner - their raw output isn't
# user-facing prose, and human-in-the-loop confirmation flows need that turn.
TERMINAL_TOOLS = {"summarize_conversation", "extract_tasks", "save_personal_memory"}


def route_after_planner(state: AgentState) -> str:
    """Route tool calls to execution and plain replies through output validation."""
    if state.get("error"):
        return END
    return tools_condition(state)


def route_after_input_guardrail(state: AgentState) -> str:
    """Stop blocked/unclear requests before they can consume LLM tokens or call a tool."""
    if state.get("guardrail_blocked") or state.get("guardrail_requires_clarification"):
        return "compact_thread"
    return "personal_query_router"


def route_after_personal_query_router(state: AgentState) -> str:
    """Execute explicit Memory writes deterministically; plan every other allowed intent."""
    if state.get("personal_intent") == "memory_write":
        return "save_personal_memory"
    return "planner"


def route_after_tools(state: AgentState) -> str:
    """End immediately after a terminal tool (its output is the final answer); otherwise loop
    back to the planner so it can phrase a reply or decide on further tool calls."""
    last = state["messages"][-1]
    if isinstance(last, ToolMessage) and last.name in TERMINAL_TOOLS:
        return END
    return "planner"


def build_graph(checkpointer):
    graph = StateGraph(AgentState)

    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("personal_query_router", personal_query_router_node)
    graph.add_node("save_personal_memory", save_explicit_personal_memory_node)
    graph.add_node("planner", planner_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("compact_thread", compact_thread_node)

    graph.set_entry_point("input_guardrail")
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {"personal_query_router": "personal_query_router", "compact_thread": "compact_thread"},
    )
    graph.add_conditional_edges(
        "personal_query_router",
        route_after_personal_query_router,
        {
            "save_personal_memory": "save_personal_memory",
            "planner": "planner",
        },
    )
    graph.add_edge("save_personal_memory", "output_guardrail")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {"tools": "tools", END: "output_guardrail"},
    )
    graph.add_conditional_edges(
        "tools", route_after_tools, {"planner": "planner", END: "output_guardrail"}
    )
    graph.add_edge("output_guardrail", "compact_thread")
    graph.add_edge("compact_thread", END)

    return graph.compile(checkpointer=checkpointer)


_settings = get_settings()
_use_postgres = _settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://", "postgres://"))

# PostgreSQL is initialized during application startup. Lightweight development and tests use
# MemorySaver so importing the graph never requires a running event loop or external database.
if _use_postgres:
    checkpointer, checkpointer_pool, agent = None, None, None
else:
    checkpointer, checkpointer_pool = MemorySaver(), None
    agent = build_graph(checkpointer)


async def init_checkpointer() -> None:
    """Build the Postgres checkpointer/pool and compile `agent` with it. Must be awaited once,
    inside the event loop that will go on to serve requests, before any /chat call."""
    global checkpointer, checkpointer_pool, agent
    if not _use_postgres:
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    scheme, _, rest = _settings.database_url.partition("://")
    conninfo = f"{scheme.split('+')[0]}://{rest}"
    pool = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=_settings.agent_checkpointer_pool_size,
        open=False,
        kwargs={"autocommit": True},
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()

    checkpointer_pool = pool
    checkpointer = saver
    agent = build_graph(checkpointer)


async def close_checkpointer() -> None:
    if checkpointer_pool is not None:
        await checkpointer_pool.close()
