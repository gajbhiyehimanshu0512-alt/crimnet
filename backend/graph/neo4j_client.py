"""
graph/neo4j_client.py — Async Neo4j connection manager and Cypher query executor.
Provides utility methods for batch upsert, path queries, and neighbor lookup.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from config import settings

logger = logging.getLogger(__name__)

# ── Constraints / Index definitions ──────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person)       REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT org_id    IF NOT EXISTS FOR (n:Organization)  REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT loc_id    IF NOT EXISTS FOR (n:Location)      REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT phone_id  IF NOT EXISTS FOR (n:PhoneNumber)   REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT veh_id    IF NOT EXISTS FOR (n:Vehicle)       REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT acct_id   IF NOT EXISTS FOR (n:BankAccount)   REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT event_id  IF NOT EXISTS FOR (n:Event)         REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT case_id   IF NOT EXISTS FOR (n:Case)          REQUIRE n.id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX person_name IF NOT EXISTS FOR (n:Person)       ON (n.name)",
    "CREATE INDEX org_name    IF NOT EXISTS FOR (n:Organization)  ON (n.name)",
    "CREATE INDEX loc_name    IF NOT EXISTS FOR (n:Location)      ON (n.name)",
    "CREATE INDEX case_name   IF NOT EXISTS FOR (n:Case)          ON (n.name)",
    "CREATE INDEX case_status IF NOT EXISTS FOR (n:Case)          ON (n.status)",
]


class Neo4jClient:
    """Singleton async Neo4j client."""

    _driver: Optional[AsyncDriver] = None

    async def connect(self):
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_url,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
        )
        logger.info("Neo4j driver initialised.")

    async def close(self):
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed.")

    async def init_constraints(self):
        """Create uniqueness constraints and indexes on startup."""
        async with self._driver.session() as session:
            for stmt in CONSTRAINTS + INDEXES:
                try:
                    await session.run(stmt)
                except Exception as e:
                    logger.warning(f"Constraint/index (may already exist): {e}")
        logger.info("Neo4j schema constraints and indexes ready.")

    # ── Core Query Helpers ────────────────────────────────────────────────────

    async def run(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Execute a Cypher query and return all records as dicts."""
        async with self._driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    async def run_write(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Execute a write transaction."""
        async with self._driver.session() as session:
            result = await session.execute_write(
                lambda tx: tx.run(query, params or {}).data()
            )
            return result

    # ── Entity Operations ─────────────────────────────────────────────────────

    async def upsert_entity(self, label: str, properties: Dict[str, Any]) -> str:
        """
        MERGE a node by id. Creates if not exists, updates on match.
        Returns the node id.
        """
        if "id" not in properties or not properties["id"]:
            properties["id"] = str(uuid.uuid4())

        # Build SET clause dynamically (exclude id from SET)
        set_items = {k: v for k, v in properties.items() if k != "id"}
        set_clause = ", ".join(f"n.{k} = ${k}" for k in set_items)

        query = f"""
        MERGE (n:{label} {{id: $id}})
        ON CREATE SET n.created_at = datetime()
        SET n.updated_at = datetime(), {set_clause}
        RETURN n.id AS id
        """
        records = await self.run(query, properties)
        return records[0]["id"] if records else properties["id"]

    async def upsert_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Dict[str, Any] = None,
    ) -> bool:
        """MERGE a relationship between two nodes by their ids."""
        props = properties or {}
        prop_str = ", ".join(f"r.{k} = $prop_{k}" for k in props)
        set_clause = f"SET r.updated_at = datetime(){', ' + prop_str if prop_str else ''}"

        params = {"src": source_id, "tgt": target_id}
        params.update({f"prop_{k}": v for k, v in props.items()})

        query = f"""
        MATCH (a {{id: $src}}), (b {{id: $tgt}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r.created_at = datetime(), r.weight = 1
        ON MATCH  SET r.weight = coalesce(r.weight, 1) + 1
        {set_clause}
        RETURN r
        """
        records = await self.run(query, params)
        return bool(records)

    # ── Graph Queries ─────────────────────────────────────────────────────────

    async def get_entity(self, entity_id: str) -> Optional[Dict]:
        """Get a single entity node by id."""
        records = await self.run(
            "MATCH (n {id: $id}) RETURN n, labels(n) AS labels",
            {"id": entity_id},
        )
        return records[0] if records else None

    async def get_neighbors(self, entity_id: str, depth: int = 1) -> Dict:
        """Get all nodes and relationships within `depth` hops."""
        query = f"""
        MATCH path = (start {{id: $id}})-[*1..{depth}]-(neighbor)
        RETURN nodes(path) AS nodes, relationships(path) AS rels
        """
        records = await self.run(query, {"id": entity_id})
        nodes, edges = {}, {}
        for row in records:
            for n in row["nodes"]:
                nodes[n["id"]] = dict(n)
            for r in row["rels"]:
                eid = f"{r.start_node['id']}__{r.end_node['id']}__{r.type}"
                edges[eid] = {
                    "source": r.start_node["id"],
                    "target": r.end_node["id"],
                    "type": r.type,
                    **dict(r),
                }
        return {"nodes": list(nodes.values()), "edges": list(edges.values())}

    async def shortest_path(self, from_id: str, to_id: str) -> List[Dict]:
        """Find shortest path between two entities."""
        query = """
        MATCH p = shortestPath((a {id: $from_id})-[*..15]-(b {id: $to_id}))
        RETURN [n IN nodes(p) | {id: n.id, name: n.name}] AS path,
               length(p) AS hops
        """
        records = await self.run(query, {"from_id": from_id, "to_id": to_id})
        return records

    async def get_full_graph(self, limit: int = 500) -> Dict:
        """Return all nodes and edges up to limit for full-network visualization."""
        query = f"""
        MATCH (n)
        WITH n LIMIT {limit}
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN collect(DISTINCT {{
            id: n.id, name: n.name, labels: labels(n),
            risk_level: n.risk_level, community_id: n.community_id,
            pagerank: n.pagerank
        }}) AS nodes,
        collect(DISTINCT {{
            source: n.id, target: m.id, type: type(r), weight: r.weight
        }}) AS edges
        """
        records = await self.run(query)
        if not records:
            return {"nodes": [], "edges": []}
        return {"nodes": records[0]["nodes"], "edges": records[0]["edges"]}

    async def get_community_nodes(self, community_id: int) -> List[Dict]:
        """Get all nodes in a specific community."""
        return await self.run(
            "MATCH (n {community_id: $cid}) RETURN n",
            {"cid": community_id},
        )

    async def search_entities(self, query: str, limit: int = 20) -> List[Dict]:
        """Full-text search across entity names and aliases."""
        cypher = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($q)
           OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower($q))
        RETURN n, labels(n) AS labels
        LIMIT $limit
        """
        return await self.run(cypher, {"q": query, "limit": limit})

    async def store_analytics(self, entity_id: str, analytics: Dict[str, Any]):
        """Write analytics results (centrality, risk) back onto a node."""
        set_items = ", ".join(f"n.{k} = ${k}" for k in analytics)
        query = f"MATCH (n {{id: $id}}) SET {set_items}"
        await self.run({"id": entity_id, **analytics} if False else query,
                       {"id": entity_id, **analytics})

    async def get_all_nodes_for_analytics(self) -> List[Dict]:
        """Fetch all nodes (id, labels, name) for graph analytics."""
        return await self.run("MATCH (n) RETURN n.id AS id, n.name AS name, labels(n) AS labels")

    async def get_all_edges_for_analytics(self) -> List[Dict]:
        """Fetch all edges for graph analytics."""
        return await self.run(
            "MATCH (a)-[r]->(b) RETURN a.id AS source, b.id AS target, type(r) AS type, r.weight AS weight"
        )


# ── Singleton ─────────────────────────────────────────────────────────────────
neo4j_client = Neo4jClient()
