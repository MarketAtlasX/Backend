import uuid
from datetime import datetime
from typing import Any, Literal
from langgraph.graph import StateGraph, END

from ..models import IntentType, ChatResponse
from ..agents import (
    IntentRouter,
    NewsAgent,
    MarketAgent,
    ImpactAgent,
    GraphAgent,
    ForecastAgent,
    RecommendationAgent,
    ReportAgent,
    SimulationAgent,
    DebateAgent,
)
from ..memory.short_term import short_term_memory
from ..memory.long_term import long_term_memory
from ..rag.retriever import seed_knowledge_base


class AgentState(dict):
    query: str
    conversation_id: str
    user_id: str
    intent: IntentType
    intent_confidence: float
    agents_used: list[str]
    sources: list[str]
    agent_responses: dict[str, Any]
    final_response: str
    confidence: float
    error: str


router = IntentRouter()
news_agent = NewsAgent()
market_agent = MarketAgent()
impact_agent = ImpactAgent()
graph_agent = GraphAgent()
forecast_agent = ForecastAgent()
recommendation_agent = RecommendationAgent()
report_agent = ReportAgent()
simulation_agent = SimulationAgent()
debate_agent = DebateAgent()


async def route_intent(state: AgentState) -> AgentState:
    history = short_term_memory.format_context(state["conversation_id"])
    context = {"conversation_context": history}

    intent, confidence = router.classify(state["query"], conversation_history=history)
    state["intent"] = intent
    state["intent_confidence"] = confidence
    state["agents_used"] = router.get_agents_for_intent(intent)
    state["agent_responses"] = {}
    state["sources"] = []

    state["_context"] = context
    return state


def decide_agents(state: AgentState) -> Literal["debate", "report", "execute_debate", "execute_report", "execute_direct", "execute_news", "execute_market", "execute_impact", "execute_graph", "execute_forecast", "execute_recommendation", "execute_simulation"]:
    intent = state["intent"]

    if intent == IntentType.REPORT:
        return "execute_report"
    if intent == IntentType.SIMULATION:
        return "execute_simulation"

    if intent == IntentType.NEWS:
        return "execute_news"
    if intent == IntentType.MARKET:
        return "execute_market"
    if intent == IntentType.IMPACT:
        return "execute_impact"
    if intent == IntentType.GRAPH:
        return "execute_graph"
    if intent == IntentType.RECOMMENDATION:
        return "execute_recommendation"

    agents = state["agents_used"]
    if len(agents) > 2:
        return "debate"
    return "execute_direct"


def _ensure_context(state: AgentState) -> None:
    if "_context" not in state:
        state["_context"] = {}
    if "agent_responses" not in state:
        state["agent_responses"] = {}
    if "sources" not in state:
        state["sources"] = []


async def execute_news(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await news_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["NewsAgent"] = result["response"]
    state["sources"].extend(result.get("sources", []))
    state["final_response"] = result["response"]
    return state


async def execute_market(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await market_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["MarketAgent"] = result["response"]
    if "market_data" in result:
        state["_context"]["market_data"] = result["market_data"]
    state["final_response"] = result["response"]
    return state


async def execute_impact(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await impact_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["ImpactAgent"] = result["response"]
    state["_context"]["impact_analysis"] = result["response"]
    state["sources"].extend(result.get("sources", []))
    state["final_response"] = result["response"]
    return state


async def execute_graph(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await graph_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["GraphAgent"] = result["response"]
    state["sources"].extend(result.get("sources", []))
    state["final_response"] = result["response"]
    return state


async def execute_forecast(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await forecast_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["ForecastAgent"] = result["response"]
    state["final_response"] = result["response"]
    return state


async def execute_recommendation(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await recommendation_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["RecommendationAgent"] = result["response"]
    state["final_response"] = result["response"]
    return state


async def execute_simulation(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await simulation_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["SimulationAgent"] = result["response"]
    state["final_response"] = result["response"]
    return state


async def execute_report(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await report_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["ReportAgent"] = result["response"]
    state["final_response"] = result["response"]
    state["sources"].extend(result.get("sources", []))
    return state


async def execute_debate(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await debate_agent.run_debate(state["query"], state.get("_context"))
    state["agent_responses"]["DebateAgent"] = result["response"]
    state["agent_responses"]["Perspectives"] = result.get("perspectives", [])
    state["final_response"] = result["response"]
    return state


async def execute_direct(state: AgentState) -> AgentState:
    _ensure_context(state)
    for agent_name in state["agents_used"]:
        if agent_name == "NewsAgent":
            r = await news_agent.process(state["query"], state.get("_context"))
        elif agent_name == "MarketAgent":
            r = await market_agent.process(state["query"], state.get("_context"))
        elif agent_name == "ImpactAgent":
            r = await impact_agent.process(state["query"], state.get("_context"))
        elif agent_name == "GraphAgent":
            r = await graph_agent.process(state["query"], state.get("_context"))
        elif agent_name == "ForecastAgent":
            r = await forecast_agent.process(state["query"], state.get("_context"))
        elif agent_name == "RecommendationAgent":
            r = await recommendation_agent.process(state["query"], state.get("_context"))
        elif agent_name == "SimulationAgent":
            r = await simulation_agent.process(state["query"], state.get("_context"))
        elif agent_name == "ReportAgent":
            r = await report_agent.process(state["query"], state.get("_context"))
        else:
            continue
        state["agent_responses"][agent_name] = r["response"]
        if "sources" in r:
            state["sources"].extend(r["sources"])

    combined = "\n\n".join([f"### {name}\n{resp}" for name, resp in state["agent_responses"].items()])
    state["final_response"] = combined
    return state


def calculate_confidence(state: AgentState) -> AgentState:
    base = state["intent_confidence"]
    num_responses = len(state["agent_responses"])
    response_bonus = min(num_responses * 0.05, 0.2)
    state["confidence"] = min(base + response_bonus, 0.95)
    return state


def store_memory(state: AgentState) -> AgentState:
    short_term_memory.add_turn(state["conversation_id"], "user", state["query"])
    short_term_memory.add_turn(state["conversation_id"], "assistant", state["final_response"])
    return state


def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("route_intent", route_intent)
    workflow.add_node("execute_news", execute_news)
    workflow.add_node("execute_market", execute_market)
    workflow.add_node("execute_impact", execute_impact)
    workflow.add_node("execute_graph", execute_graph)
    workflow.add_node("execute_forecast", execute_forecast)
    workflow.add_node("execute_recommendation", execute_recommendation)
    workflow.add_node("execute_simulation", execute_simulation)
    workflow.add_node("execute_report", execute_report)
    workflow.add_node("execute_debate", execute_debate)
    workflow.add_node("execute_direct", execute_direct)
    workflow.add_node("calculate_confidence", calculate_confidence)
    workflow.add_node("store_memory", store_memory)

    workflow.set_entry_point("route_intent")

    workflow.add_conditional_edges(
        "route_intent",
        decide_agents,
        {
            "debate": "execute_debate",
            "report": "execute_report",
            "execute_debate": "execute_debate",
            "execute_report": "execute_report",
            "execute_direct": "execute_direct",
            "execute_news": "execute_news",
            "execute_market": "execute_market",
            "execute_impact": "execute_impact",
            "execute_graph": "execute_graph",
            "execute_forecast": "execute_forecast",
            "execute_recommendation": "execute_recommendation",
            "execute_simulation": "execute_simulation",
        }
    )

    execution_nodes = [
        "execute_news", "execute_market", "execute_impact", "execute_graph",
        "execute_forecast", "execute_recommendation", "execute_simulation",
        "execute_report", "execute_debate", "execute_direct",
    ]
    for node in execution_nodes:
        workflow.add_edge(node, "calculate_confidence")

    workflow.add_edge("calculate_confidence", "store_memory")
    workflow.add_edge("store_memory", END)

    return workflow.compile()


graph = build_workflow()


async def run_chat(query: str, conversation_id: str = None, user_id: str = "default") -> ChatResponse:
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    await seed_knowledge_base()

    initial_state = AgentState({
        "query": query,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "intent": None,
        "intent_confidence": 0.0,
        "agents_used": [],
        "sources": [],
        "agent_responses": {},
        "final_response": "",
        "confidence": 0.0,
        "error": "",
        "_context": {},
    })

    result = await graph.ainvoke(initial_state)

    return ChatResponse(
        conversation_id=conversation_id,
        query=query,
        response=result.get("final_response", "No response generated."),
        intent=result.get("intent", IntentType.IMPACT),
        agents_used=result.get("agents_used", []),
        confidence=result.get("confidence", 0.5),
        sources=list(set(result.get("sources", []))),
    )
