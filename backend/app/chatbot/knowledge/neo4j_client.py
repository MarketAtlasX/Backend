import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")


def get_driver():
    uri = NEO4J_URI
    user = NEO4J_USER
    password = NEO4J_PASSWORD
    if not uri or not user or not password:
        return None
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception:
        return None


class Neo4jClient:
    def __init__(self):
        self.driver = get_driver()

    @property
    def available(self) -> bool:
        return self.driver is not None

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, cypher: str, params: dict[str, Any] = None) -> list[dict[str, Any]]:
        if not self.driver:
            return []
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params or {})
                return [r.data() for r in result]
        except Exception as e:
            logger.warning(f"Neo4j query failed: {e}")
            return []

    def merge_entity(self, name: str, entity_type: str = "Entity", properties: dict[str, Any] = None):
        if not self.driver:
            return
        props = properties or {}
        cypher = (
            f"MERGE (n:{entity_type} {{name: $name}}) "
            f"SET n += $props"
        )
        try:
            with self.driver.session() as session:
                session.run(cypher, {"name": name, "props": props})
        except Exception:
            pass

    def merge_relation(self, source: str, target: str, relation: str, target_type: str = "Entity", properties: dict[str, Any] = None):
        if not self.driver:
            return
        props = properties or {}
        cypher = (
            f"MERGE (a {{name: $source}}) "
            f"MERGE (b:{target_type} {{name: $target}}) "
            f"MERGE (a)-[r:{relation}]->(b) "
            f"SET r += $props"
        )
        try:
            with self.driver.session() as session:
                session.run(cypher, {"source": source, "target": target, "props": props})
        except Exception:
            pass

    def get_entity(self, name: str) -> Optional[dict]:
        if not self.driver:
            return None
        cypher = "MATCH (n {name: $name}) RETURN n LIMIT 1"
        try:
            with self.driver.session() as session:
                result = session.run(cypher, {"name": name})
                record = result.single()
                return record.data() if record else None
        except Exception:
            return None

    def get_relations(self, entity_name: str, depth: int = 1) -> list[dict]:
        if not self.driver:
            return []
        cypher = (
            f"MATCH (n {{name: $name}})-[r *1..{depth}]-(m) "
            f"RETURN n, r, m LIMIT 50"
        )
        try:
            with self.driver.session() as session:
                result = session.run(cypher, {"name": entity_name})
                return [r.data() for r in result]
        except Exception:
            return []

    def query_related_entities(self, entity_name: str, relation_type: str = None) -> list[dict]:
        if not self.driver:
            return []
        rel_filter = f":{relation_type}" if relation_type else ""
        cypher = (
            f"MATCH (n {{name: $name}})-[r{rel_filter}]->(m) "
            f"RETURN m.name AS target, type(r) AS relation, m"
        )
        try:
            with self.driver.session() as session:
                result = session.run(cypher, {"name": entity_name})
                return [r.data() for r in result]
        except Exception:
            return []

    def get_graph_context(self, entity_name: str, depth: int = 2) -> str:
        entities = self.get_relations(entity_name, depth)
        if not entities:
            return ""
        lines = []
        seen = set()
        for e in entities:
            for key, val in e.items():
                if isinstance(val, dict):
                    n = val.get("name", "")
                    if n and n not in seen:
                        lines.append(f"- {n}")
                        seen.add(n)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            n = item.get("name", "")
                            if n and n not in seen:
                                lines.append(f"- {n}")
                                seen.add(n)
        return "\n".join(lines) if lines else ""
