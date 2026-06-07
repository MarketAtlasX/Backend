"""Simple Neo4j persistence helpers for MarketAtlas."""
from typing import Dict, Any, List, Tuple, Optional
import os

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None


def _get_driver() -> Optional[object]:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or GraphDatabase is None:
        return None
    auth = (user, password) if user and password else None
    if auth:
        return GraphDatabase.driver(uri, auth=auth)
    return GraphDatabase.driver(uri)


def write_graph(nodes: Dict[str, Dict[str, Any]], relations: List[Tuple[str, str, str]], driver=None) -> bool:
    if driver is None:
        driver = _get_driver()
    if driver is None:
        return False

    def _tx_fn(tx, nodes, relations):
        for name, props in nodes.items():
            tx.run(
                "MERGE (n:Entity {name: $name}) SET n += $props",
                name=name,
                props=props or {},
            )
        for a, rel, b in relations:
            tx.run(
                "MERGE (a:Entity {name: $a}) MERGE (b:Entity {name: $b}) MERGE (a)-[r:`" + rel + "`]->(b)",
                a=a,
                b=b,
            )

    try:
        with driver.session() as session:
            session.write_transaction(_tx_fn, nodes, relations)
        return True
    except Exception:
        return False
