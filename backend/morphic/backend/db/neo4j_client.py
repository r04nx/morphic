"""
Neo4j client — manages the driver singleton and provides graph helpers.

Node labels:  Incident, Service, Order, User
Relationships: ORIGINATED_IN, AFFECTED, TRIGGERED, CORRELATES_WITH
"""

import logging
from typing import Any

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from config import Config

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD),
        )
        logger.info("Neo4j driver initialised at %s", Config.NEO4J_URI)
    return _driver


def close_driver() -> None:
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def ping() -> bool:
    try:
        get_driver().verify_connectivity()
        return True
    except ServiceUnavailable:
        return False


# ---------------------------------------------------------------------------
# Graph write helpers
# ---------------------------------------------------------------------------

def upsert_incident_graph(incident: dict[str, Any]) -> None:
    """
    Create/update an Incident node and link it to its Service node.
    Relationships:
        (Incident)-[:ORIGINATED_IN]->(Service)
    """
    cypher = """
        MERGE (i:Incident {trace_id: $trace_id})
        SET i.timestamp       = $timestamp,
            i.classification  = $classification,
            i.blast_radius    = $blast_radius,
            i.root_cause      = $root_cause,
            i.status          = $status,
            i.confidence_score = $confidence_score,
            i.summary         = $summary

        MERGE (s:Service {name: $service})

        MERGE (i)-[:ORIGINATED_IN]->(s)
    """
    params = {
        "trace_id":        incident.get("trace_id", ""),
        "timestamp":       str(incident.get("timestamp", "")),
        "classification":  incident.get("classification", ""),
        "blast_radius":    incident.get("blast_radius", "LOW"),
        "root_cause":      incident.get("root_cause", ""),
        "status":          incident.get("status", "active"),
        "confidence_score": float(incident.get("confidence_score", 0.0)),
        "summary":         incident.get("summary", ""),
        "service":         incident.get("service", "unknown"),
    }
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, params)
    except Exception as exc:
        logger.warning("Neo4j upsert_incident_graph failed: %s", exc)


def link_order_to_incident(trace_id: str, order_id: str) -> None:
    """(Incident)-[:AFFECTED]->(Order)"""
    cypher = """
        MERGE (i:Incident {trace_id: $trace_id})
        MERGE (o:Order {order_id: $order_id})
        MERGE (i)-[:AFFECTED]->(o)
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, {"trace_id": trace_id, "order_id": order_id})
    except Exception as exc:
        logger.warning("Neo4j link_order_to_incident failed: %s", exc)


def link_user_to_incident(trace_id: str, user_id: str) -> None:
    """(Incident)-[:AFFECTED]->(User)"""
    cypher = """
        MERGE (i:Incident {trace_id: $trace_id})
        MERGE (u:User {user_id: $user_id})
        MERGE (i)-[:AFFECTED]->(u)
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, {"trace_id": trace_id, "user_id": user_id})
    except Exception as exc:
        logger.warning("Neo4j link_user_to_incident failed: %s", exc)


def link_rca_to_incident(trace_id: str, rca: dict[str, Any]) -> None:
    """Attach RCA metadata properties to the Incident node and create a
    TRIGGERED relationship to the target Java class node."""
    cypher = """
        MERGE (i:Incident {trace_id: $trace_id})
        SET i.rca_classification = $classification,
            i.rca_blast_radius   = $blast_radius,
            i.rca_confidence     = $confidence_score,
            i.rca_root_cause     = $root_cause

        MERGE (c:JavaClass {name: $target_class})
        MERGE (i)-[:TRIGGERED]->(c)
    """
    params = {
        "trace_id":        trace_id,
        "classification":  rca.get("classification", ""),
        "blast_radius":    rca.get("blast_radius", "LOW"),
        "confidence_score": float(rca.get("confidence_score", 0.0)),
        "root_cause":      rca.get("root_cause", ""),
        "target_class":    rca.get("suggested_fix", {}).get("target_class", "Unknown"),
    }
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, params)
    except Exception as exc:
        logger.warning("Neo4j link_rca_to_incident failed: %s", exc)


def correlate_incidents(trace_id_a: str, trace_id_b: str) -> None:
    """(Incident A)-[:CORRELATES_WITH]->(Incident B)"""
    cypher = """
        MATCH (a:Incident {trace_id: $a})
        MATCH (b:Incident {trace_id: $b})
        MERGE (a)-[:CORRELATES_WITH]->(b)
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, {"a": trace_id_a, "b": trace_id_b})
    except Exception as exc:
        logger.warning("Neo4j correlate_incidents failed: %s", exc)


def update_incident_status_graph(trace_id: str, status: str) -> None:
    cypher = """
        MATCH (i:Incident {trace_id: $trace_id})
        SET i.status = $status
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            session.run(cypher, {"trace_id": trace_id, "status": status})
    except Exception as exc:
        logger.warning("Neo4j update_incident_status_graph failed: %s", exc)


def get_incident_graph(trace_id: str) -> dict[str, Any]:
    """Return the incident node and its first-degree neighbours."""
    cypher = """
        MATCH (i:Incident {trace_id: $trace_id})
        OPTIONAL MATCH (i)-[r]->(n)
        RETURN i, collect({rel: type(r), node: n}) AS neighbours
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            result = session.run(cypher, {"trace_id": trace_id})
            record = result.single()
            if not record:
                return {}
            node = dict(record["i"])
            neighbours = [
                {"relationship": nb["rel"], "node": dict(nb["node"])}
                for nb in record["neighbours"]
                if nb["node"] is not None
            ]
            return {"incident": node, "neighbours": neighbours}
    except Exception as exc:
        logger.warning("Neo4j get_incident_graph failed: %s", exc)
        return {}


def get_all_incidents_cytoscape() -> dict[str, Any]:
    """Return all incidents (with blast_radius) and related nodes/edges in Cytoscape format."""
    cypher = """
        MATCH (i:Incident)
        WHERE i.blast_radius IS NOT NULL
        
        OPTIONAL MATCH (i)-[r]->(m)
        WHERE type(r) IN ['ORIGINATED_IN', 'AFFECTED', 'TRIGGERED', 'CORRELATES_WITH', 'HEALED']
        
        RETURN i, r, m
    """
    try:
        with get_driver().session(database=Config.NEO4J_DATABASE) as session:
            result = session.run(cypher)
            
            nodes = {}
            edges = []
            
            for record in result:
                i = record["i"]
                r = record["r"]
                m = record["m"]
                
                if not i:
                    continue

                i_id = f"incident-{i.get('trace_id') or getattr(i, 'element_id', 'unknown')}"
                if i_id not in nodes:
                    i_label = i.get("classification") or i.get("summary") or "Unknown Incident"
                    nodes[i_id] = {
                        "data": {
                            "id": str(i_id),
                            "label": str(i_label)[:30],
                            "type": "incident",
                            "severity": str(i.get("blast_radius", "LOW")),
                            "confidence": float(i.get("confidence_score") or 0.0),
                            "status": str(i.get("status", "unknown")),
                            "trace_id": str(i.get("trace_id", "")),
                            "root_cause": str(i.get("root_cause", "")),
                            "classification": str(i.get("classification", ""))
                        }
                    }
                
                if m is not None and r is not None:
                    labels = list(m.labels)
                    m_type = labels[0].lower() if labels else "unknown"
                    
                    if "Service" in labels:
                        m_id = f"service-{m.get('name') or getattr(m, 'element_id', 'unknown')}"
                        label = str(m.get("name") or "Unknown Service")
                    elif "Order" in labels:
                        m_id = f"order-{m.get('order_id') or getattr(m, 'element_id', 'unknown')}"
                        label = str(m.get("order_id") or "Unknown Order")
                    elif "User" in labels:
                        m_id = f"user-{m.get('user_id') or getattr(m, 'element_id', 'unknown')}"
                        label = str(m.get("user_id") or "Unknown User")
                    elif "Incident" in labels:
                        m_id = f"incident-{m.get('trace_id') or getattr(m, 'element_id', 'unknown')}"
                        m_label = m.get("classification") or m.get("summary") or "Unknown Incident"
                        label = str(m_label)[:30]
                        if m_id not in nodes:
                            nodes[m_id] = {
                                "data": {
                                    "id": str(m_id),
                                    "label": label,
                                    "type": "incident",
                                    "severity": str(m.get("blast_radius", "LOW")),
                                    "confidence": float(m.get("confidence_score") or 0.0),
                                    "status": str(m.get("status", "unknown")),
                                    "trace_id": str(m.get("trace_id", "")),
                                    "root_cause": str(m.get("root_cause", "")),
                                    "classification": str(m.get("classification", ""))
                                }
                            }
                    elif "JavaClass" in labels:
                        m_id = f"javaclass-{m.get('name') or getattr(m, 'element_id', 'unknown')}"
                        label = str(m.get("name") or "Unknown Class")
                    else:
                        m_id = f"node-{getattr(m, 'element_id', 'unknown')}"
                        label = "Unknown"

                    if m_id not in nodes:
                        nodes[m_id] = {
                            "data": {
                                "id": str(m_id),
                                "label": label,
                                "type": str(m_type)
                            }
                        }
                        
                    edge_id = f"edge-{getattr(r, 'element_id', hash(r))}"
                    edges.append({
                        "data": {
                            "id": str(edge_id),
                            "source": str(i_id),
                            "target": str(m_id),
                            "label": str(r.type)
                        }
                    })
                    
            return {
                "nodes": list(nodes.values()),
                "edges": edges
            }
    except Exception as exc:
        import traceback
        logger.warning("Neo4j get_all_incidents_cytoscape failed: %s", exc)
        return {"nodes": [], "edges": [], "error": str(exc), "traceback": traceback.format_exc()}
