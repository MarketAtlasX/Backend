import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from ..agents import (
    DebateAgent,
    EventSimilarityAgent,
    ForecastAgent,
    GraphAgent,
    ImpactAgent,
    IntentRouter,
    MarketAgent,
    NewsAgent,
    RecommendationAgent,
    ReportAgent,
    RiskAgent,
    SimulationAgent,
)
from ..explain.attention_explainer import AttentionExplainer
from ..explain.graph_explainer import GraphExplainer
from ..explain.shap_explainer import SHAPExplainer
from ..memory.short_term import short_term_memory
from ..models import ChatResponse, IntentType
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
risk_agent = RiskAgent()
event_similarity_agent = EventSimilarityAgent()
shap_explainer = SHAPExplainer()
attention_explainer = AttentionExplainer()
graph_explainer = GraphExplainer()


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


def decide_agents(state: AgentState) -> Literal["debate", "report", "execute_debate", "execute_report", "execute_direct", "execute_news", "execute_market", "execute_impact", "execute_graph", "execute_forecast", "execute_recommendation", "execute_simulation", "execute_similarity", "execute_risk"]:
    intent = state["intent"]
    routing_map = {
        IntentType.REPORT: "execute_report",
        IntentType.SIMULATION: "execute_simulation",
        IntentType.SIMILARITY: "execute_similarity_pipeline",
        IntentType.NEWS: "execute_news",
        IntentType.MARKET: "execute_market",
        IntentType.IMPACT: "execute_impact",
        IntentType.GRAPH: "execute_graph",
        IntentType.RECOMMENDATION: "execute_recommendation",
        IntentType.RISK: "execute_risk",
    }
    if intent in routing_map:
        return routing_map[intent]

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


async def execute_similarity(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await event_similarity_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["EventSimilarityAgent"] = result["response"]
    if "similarity_data" in result:
        state["_context"]["similarity"] = result["similarity_data"]
    if "explanations" in result:
        state["_context"]["explanations"] = result["explanations"]
    if "explanation_text" in result:
        state["_context"]["explanation_text"] = result["explanation_text"]
    state["final_response"] = result["response"]
    return state


async def execute_similarity_pipeline(state: AgentState) -> AgentState:
    _ensure_context(state)
    query = state["query"]
    ctx = state.get("_context", {})

    news_res = await news_agent.process(query, ctx)
    similarity_res = await event_similarity_agent.process(query, ctx)
    impact_res = await impact_agent.process(query, ctx)
    forecast_res = await forecast_agent.process(query, ctx)
    report_res = await report_agent.process(query, ctx)

    state["agent_responses"]["NewsAgent"] = news_res["response"]
    state["agent_responses"]["EventSimilarityAgent"] = similarity_res["response"]
    state["agent_responses"]["ImpactAgent"] = impact_res["response"]
    state["agent_responses"]["ForecastAgent"] = forecast_res["response"]
    state["agent_responses"]["ReportAgent"] = report_res["response"]

    similarity_data = similarity_res.get("similarity_data", {})
    explanation_text = similarity_res.get("explanation_text", "")

    full_report = event_similarity_agent.format_full_report(
        query=query,
        similarity_data=similarity_data,
        news_response=news_res["response"],
        impact_response=impact_res["response"],
        forecast_response=forecast_res["response"],
        report_response=report_res["response"],
        explanation_text=explanation_text,
    )

    state["final_response"] = full_report
    state["_context"]["similarity"] = similarity_data
    if "explanations" in similarity_res:
        state["_context"]["explanations"] = similarity_res["explanations"]
    return state


async def execute_report(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await report_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["ReportAgent"] = result["response"]
    state["final_response"] = result["response"]
    state["sources"].extend(result.get("sources", []))
    return state


async def execute_risk(state: AgentState) -> AgentState:
    _ensure_context(state)
    result = await risk_agent.process(state["query"], state.get("_context"))
    state["agent_responses"]["RiskAgent"] = result["response"]
    if "risk_indices" in result:
        state["_context"]["risk_indices"] = result["risk_indices"]
    state["final_response"] = result["response"]
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
        elif agent_name == "EventSimilarityAgent":
            r = await event_similarity_agent.process(state["query"], state.get("_context"))
        elif agent_name == "RiskAgent":
            r = await risk_agent.process(state["query"], state.get("_context"))
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


async def calculate_confidence(state: AgentState) -> AgentState:
    _ensure_context(state)
    base = state["intent_confidence"]
    num_responses = len(state["agent_responses"])
    response_bonus = min(num_responses * 0.05, 0.2)
    state["confidence"] = min(base + response_bonus, 0.95)

    query = state["query"]
    intent = state["intent"]
    ctx = state.get("_context", {})

    explanations = {}
    try:
        shap_result = await shap_explainer.explain(prediction=intent.value, context={"query": query, "market_data": ctx.get("market_data", {})})
        if shap_result.shap:
            explanations["shap"] = shap_result.shap.model_dump()
    except Exception:
        pass

    try:
        attn_result = await attention_explainer.explain(context={"query": query, "similar_events": ctx.get("similarity", {}).get("similar_events", [])})
        if attn_result.attention:
            explanations["attention"] = attn_result.attention.model_dump()
    except Exception:
        pass

    try:
        graph_result = await graph_explainer.explain(context={"query": query, "entities": ctx.get("entities", [])})
        if graph_result.graph:
            explanations["graph"] = graph_result.graph.model_dump()
    except Exception:
        pass

    if explanations:
        state["_context"]["explanations"] = explanations

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
    workflow.add_node("execute_similarity", execute_similarity)
    workflow.add_node("execute_similarity_pipeline", execute_similarity_pipeline)
    workflow.add_node("execute_report", execute_report)
    workflow.add_node("execute_risk", execute_risk)
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
            "execute_similarity": "execute_similarity",
            "execute_similarity_pipeline": "execute_similarity_pipeline",
            "execute_risk": "execute_risk",
        }
    )

    execution_nodes = [
        "execute_news", "execute_market", "execute_impact", "execute_graph",
        "execute_forecast", "execute_recommendation", "execute_simulation",
        "execute_similarity", "execute_similarity_pipeline", "execute_report",
        "execute_risk", "execute_debate", "execute_direct",
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
        explanations=result.get("_context", {}).get("explanations"),
    )
