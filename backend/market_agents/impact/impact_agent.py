import networkx as nx
from typing import Dict, Any, List, Tuple
from market_agents.ingest.impact_api import fetch_gdelt_events, fetch_acled_events, fetch_eia_data


def _persist_graph(nodes: Dict[str, Dict[str, Any]], relations: List[Tuple[str, str, str]]):
    try:
        from market_agents.persistence import neo4j_client
        import os
        if os.environ.get("NEO4J_URI"):
            try:
                return neo4j_client.write_graph(nodes, relations)
            except Exception:
                return False
    except Exception:
        return False
    return False


class ImpactAgent:
    def __init__(self):
        self.g = nx.DiGraph()

    def ingest(self, state: Dict[str, Any]):
        text = state.get("text", "")
        state["text"] = text
        state.setdefault("gdelt", fetch_gdelt_events())
        state.setdefault("acled", fetch_acled_events())
        state.setdefault("eia", fetch_eia_data("TOTAL.STOCKS"))
        return state

    def extract(self, state: Dict[str, Any]):
        text = state.get("text", "")
        entities = set()
        relations = []
        for part in text.split("."):
            part = part.strip()
            if not part:
                continue
            if "sanction" in part.lower():
                words = part.split()
                if len(words) >= 2:
                    entities.add(words[0])
                    entities.add(words[-1])
                    relations.append((words[0], "sanctioned", words[-1]))
            if "attack" in part.lower() or "strike" in part.lower():
                words = part.split()
                entities.add(words[0])
                entities.add(words[-1])
                relations.append((words[0], "attacked", words[-1]))
        if not entities:
            entities.add("doc")
        state["entities"] = list(entities)
        state["relations"] = relations
        return state

    def store(self, state: Dict[str, Any]):
        for e in state.get("entities", []):
            if e not in self.g:
                self.g.add_node(e, severity=0.0)
        for a, rel, b in state.get("relations", []):
            self.g.add_edge(a, b, relation=rel)
        text = state.get("text", "")
        risk_words = ["attack", "war", "sanction", "crisis", "collapse", "strike"]
        score = 0
        for w in risk_words:
            score += text.lower().count(w)
        local = min(1.0, score / 5.0)
        if "doc" in self.g.nodes:
            self.g.nodes["doc"]["severity"] = local
        else:
            for n in self.g.nodes:
                self.g.nodes[n]["severity"] = max(self.g.nodes[n].get("severity", 0.0), local)
        state["local_severity"] = local
        return state

    def propagate(self, state: Dict[str, Any]):
        decay = 0.5
        for node in list(self.g.nodes):
            base = self.g.nodes[node].get("severity", 0.0)
            propagated = base
            for source in self.g.predecessors(node):
                s = self.g.nodes[source].get("severity", 0.0)
                propagated = max(propagated, s * decay)
            self.g.nodes[node]["severity"] = propagated
        comp = 0.0
        for n in self.g.nodes:
            comp = max(comp, self.g.nodes[n].get("severity", 0.0))
        state["composite_risk"] = float(max(0.0, min(1.0, comp)))
        return state

    def output(self, state: Dict[str, Any]):
        state["graph_summary"] = {n: dict(self.g.nodes[n]) for n in self.g.nodes}
        relations = []
        for a, b in self.g.edges:
            rel = self.g.edges[a, b].get("relation")
            relations.append((a, rel or "related", b))
        state["relations"] = relations
        try:
            _persist_graph(state["graph_summary"], relations)
        except Exception:
            pass
        return state
