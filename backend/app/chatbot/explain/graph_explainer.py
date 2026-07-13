from typing import Any

from ..knowledge.neo4j_client import Neo4jClient
from ..pipeline_adapter import run_graph_path_pipeline, run_entity_extraction_pipeline
from .base import BaseExplainer
from .models import GraphExplanation, GraphPathStep, ExplanationResult


SECTOR_TICKER_MAP = {
    "Energy": "XLE", "Defense": "ITA", "Technology": "XLK",
    "Semiconductors": "SMH", "Financials": "XLF", "Healthcare": "XLV",
    "Airlines": "JETS", "Shipping": "SEA", "Manufacturing": "XLI",
    "Agriculture": "DBA", "Insurance": "KIE", "Gold & Precious Metals": "GDX",
    "Travel & Hospitality": "PEJ", "Retail": "XRT", "Utilities": "XLU",
    "Cybersecurity": "CIBR", "Real Estate": "XLRE", "Consumer Discretionary": "XLY",
    "E-commerce": "IBUY", "Chemicals": "XLB",
}


class GraphExplainer(BaseExplainer):
    def __init__(self):
        self.neo4j = Neo4jClient()

    async def explain(self, prediction: str = "", context: dict[str, Any] | None = None) -> ExplanationResult:
        ctx = context or {}
        entities = ctx.get("entities", [])
        sectors = ctx.get("sectors", [])
        query = ctx.get("query", ctx.get("original_query", ""))

        if not entities and not sectors:
            entities = self._extract_entities_from_query(query)

        pipeline_result = await run_graph_path_pipeline(
            entities=entities or ["Geopolitical Event"],
            sectors=sectors or ["Energy", "Defense"],
        )
        kg_result = pipeline_result.get("kg_results", {})
        pipeline_paths = pipeline_result.get("graph_paths", [])
        grounded_facts = pipeline_result.get("grounded_facts", [])

        path = self._build_reasoning_path(
            entities, sectors, query,
            pipeline_paths=pipeline_paths, grounded_facts=grounded_facts,
        )
        summary = self._summarize_path(path, entities, sectors)

        graph_exp = GraphExplanation(
            start_entity=path[0].source if path else (entities[0] if entities else "Unknown"),
            end_entity=path[-1].target if path else (sectors[0] if sectors else "Market"),
            path=path,
            path_summary=summary,
        )

        return ExplanationResult(graph=graph_exp, kg_facts=grounded_facts)

    def _extract_entities_from_query(self, query: str) -> list[str]:
        text_lower = query.lower()
        known = {
            "iran": "Iran", "israel": "Israel", "russia": "Russia", "ukraine": "Ukraine",
            "china": "China", "taiwan": "Taiwan", "us": "United States", "usa": "United States",
            "middle east": "Middle East", "europe": "Europe", "nato": "NATO", "uk": "UK",
            "saudi arabia": "Saudi Arabia", "yemen": "Yemen", "afghanistan": "Afghanistan",
            "north korea": "North Korea", "iraq": "Iraq", "syria": "Syria",
        }
        found = []
        for kw, name in known.items():
            if kw in text_lower:
                found.append(name)
        if not found:
            found = ["Geopolitical Event"]
        return found

    def _build_reasoning_path(
        self,
        entities: list,
        sectors: list,
        query: str,
        pipeline_paths: list[dict] | None = None,
        grounded_facts: list[str] | None = None,
    ) -> list[GraphPathStep]:
        path = []
        text_lower = query.lower()

        if pipeline_paths:
            for pp in pipeline_paths:
                source = pp.get("source", pp.get("from", "Unknown"))
                relation = pp.get("relation", pp.get("edge", "affects"))
                target = pp.get("target", pp.get("to", "Market"))
                path.append(GraphPathStep(source=source, relation=relation, target=target))
            if path:
                return path

        try:
            if self.neo4j.available:
                for entity in entities[:2]:
                    relations = self.neo4j.get_relations(entity, depth=2)
                    for rel in relations[:3]:
                        if isinstance(rel, dict):
                            path.append(GraphPathStep(
                                source=rel.get("source", entity),
                                relation=rel.get("relation", "affects"),
                                target=rel.get("target", "Market"),
                            ))
        except Exception:
            pass

        if not path:
            start = entities[0] if entities else "Geopolitical Event"
            for sector in sectors[:2]:
                path.append(GraphPathStep(
                    source=start,
                    relation="disrupts" if any(w in text_lower for w in ["conflict", "war", "attack", "tension"]) else "influences",
                    target=sector,
                ))
                ticker = SECTOR_TICKER_MAP.get(sector, f"{sector} ETF")
                path.append(GraphPathStep(source=sector, relation="prices", target=ticker))
                start = sector

            if not sectors:
                guessed_sectors = []
                if any(w in text_lower for w in ["oil", "gas", "energy"]):
                    guessed_sectors.append("Energy")
                if any(w in text_lower for w in ["defense", "military", "weapon"]):
                    guessed_sectors.append("Defense")
                if any(w in text_lower for w in ["tech", "semiconductor", "chip"]):
                    guessed_sectors.append("Technology")
                if not guessed_sectors:
                    guessed_sectors = ["Energy Sector", "Defense Sector"]

                start = entities[0] if entities else "Geopolitical Event"
                for sector in guessed_sectors:
                    path.append(GraphPathStep(source=start, relation="impacts", target=sector))
                    ticker = SECTOR_TICKER_MAP.get(sector, f"{sector} ETF")
                    path.append(GraphPathStep(source=sector, relation="drives", target=ticker))
                    start = sector

        return path

    def _summarize_path(self, path: list, entities: list, sectors: list) -> str:
        if not path:
            return "No reasoning path available."
        entities_str = ", ".join(entities[:3]) if entities else "Geopolitical event"
        sectors_str = ", ".join(sectors[:3]) if sectors else "impacted sectors"
        return (
            f"Reasoning chain: {entities_str} -> related sectors ({sectors_str}) -> market instruments. "
            "Each arrow represents a causal or correlational relationship derived from the knowledge graph."
        )
