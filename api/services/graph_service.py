"""TraceShield AI — Graph Service.

Serializes bounded FalkorDB subgraphs and node neighborhoods for the Cytoscape frontend,
without exposing raw database credentials or internal Cypher logic in API routes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from api.schemas import (
    GraphEdge,
    GraphMeta,
    GraphNode,
    GraphResponse,
    NeighborsResponse,
)
from graph_db import get_graph

logger = logging.getLogger("traceshield.graph")

SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "credential", "auth_token"}


def sanitize_properties(props: Dict[str, Any]) -> Dict[str, Any]:
    """Strip sensitive fields before returning graph node/edge properties to clients."""
    clean: Dict[str, Any] = {}
    for k, v in props.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            clean[k] = "[REDACTED]"
        else:
            clean[k] = v
    return clean


def get_bounded_graph(
    project_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    depth: int = 3,
    limit: int = 100,
) -> GraphResponse:
    """Retrieve bounded nodes and edges formatted for Cytoscape graph exploration."""
    depth = max(1, min(depth, 5))
    limit = max(1, min(limit, 500))

    nodes_by_id: Dict[str, GraphNode] = {}
    edges_by_id: Dict[str, GraphEdge] = {}
    truncated = False

    try:
        graph = get_graph()

        if finding_id:
            # Subgraph rooted at specific finding
            query = f"""
                MATCH path = (f:Finding {{id:$finding_id}})-[r*1..{depth}]-(target)
                RETURN path
                LIMIT $limit
            """
            params = {"finding_id": finding_id.strip(), "limit": limit}
            res = graph.ro_query(query, params=params).result_set

            for row in res:
                path = row[0]
                # In FalkorDB, path contains nodes and relationships
                for node in getattr(path, "nodes", []):
                    nid = getattr(node, "properties", {}).get("id") or str(getattr(node, "id", ""))
                    label = getattr(node, "labels", ["Entity"])[0] if getattr(node, "labels", None) else "Entity"
                    props = sanitize_properties(dict(getattr(node, "properties", {})))
                    if nid and nid not in nodes_by_id:
                        nodes_by_id[nid] = GraphNode(id=nid, label=label, properties=props)

                for rel in getattr(path, "relationships", []):
                    # Extract source and target IDs
                    src_id = None
                    tgt_id = None
                    # Attempt property lookup on connected nodes
                    if hasattr(rel, "src_node"):
                        src_id = rel.src_node.properties.get("id") or str(rel.src_node.id)
                    if hasattr(rel, "dest_node"):
                        tgt_id = rel.dest_node.properties.get("id") or str(rel.dest_node.id)

                    rel_type = getattr(rel, "relation", getattr(rel, "type", "CONNECTED_TO"))
                    eid = f"edge-{src_id}-{rel_type}-{tgt_id}"
                    if src_id and tgt_id and eid not in edges_by_id:
                        edges_by_id[eid] = GraphEdge(
                            id=eid,
                            source=src_id,
                            target=tgt_id,
                            type=str(rel_type),
                            properties=sanitize_properties(dict(getattr(rel, "properties", {}))),
                        )

            if len(res) >= limit:
                truncated = True

        else:
            # General project-bounded graph query
            query = """
                MATCH (source)-[rel]->(target)
                RETURN source.id, labels(source), properties(source),
                       target.id, labels(target), properties(target),
                       type(rel), properties(rel)
                LIMIT $limit
            """
            rows = graph.ro_query(query, params={"limit": limit}).result_set
            for row in rows:
                src_id, src_labels, src_props, tgt_id, tgt_labels, tgt_props, r_type, r_props = row
                s_id = str(src_id or "")
                t_id = str(tgt_id or "")

                if s_id and s_id not in nodes_by_id:
                    s_label = src_labels[0] if src_labels else "Node"
                    nodes_by_id[s_id] = GraphNode(
                        id=s_id, label=s_label, properties=sanitize_properties(dict(src_props or {}))
                    )

                if t_id and t_id not in nodes_by_id:
                    t_label = tgt_labels[0] if tgt_labels else "Node"
                    nodes_by_id[t_id] = GraphNode(
                        id=t_id, label=t_label, properties=sanitize_properties(dict(tgt_props or {}))
                    )

                if s_id and t_id:
                    eid = f"edge-{s_id}-{r_type}-{t_id}"
                    if eid not in edges_by_id:
                        edges_by_id[eid] = GraphEdge(
                            id=eid,
                            source=s_id,
                            target=t_id,
                            type=str(r_type or "CONNECTED_TO"),
                            properties=sanitize_properties(dict(r_props or {})),
                        )

            if len(rows) >= limit:
                truncated = True

    except Exception as exc:
        logger.error("Failed to query bounded graph from FalkorDB: %s", exc)

    return GraphResponse(
        nodes=list(nodes_by_id.values()),
        edges=list(edges_by_id.values()),
        meta=GraphMeta(
            node_count=len(nodes_by_id),
            edge_count=len(edges_by_id),
            truncated=truncated,
        ),
    )


def get_node_neighbors(
    node_id: str,
    direction: str = "both",
    relationship_type: Optional[str] = None,
    limit: int = 50,
) -> Optional[NeighborsResponse]:
    """Retrieve neighboring nodes and connecting edges for a selected node."""
    norm_id = node_id.strip()
    limit = max(1, min(limit, 200))
    direction = direction.lower()
    if direction not in ("in", "out", "both"):
        direction = "both"

    try:
        graph = get_graph()
        # First verify the root node exists
        root_query = "MATCH (n {id:$id}) RETURN n.id, labels(n), properties(n)"
        root_res = graph.ro_query(root_query, params={"id": norm_id}).result_set
        if not root_res or not root_res[0]:
            return None

        r_id, r_labels, r_props = root_res[0]
        central_node = GraphNode(
            id=str(r_id),
            label=r_labels[0] if r_labels else "Node",
            properties=sanitize_properties(dict(r_props or {})),
        )

        # Build neighbor query
        rel_spec = f":{relationship_type.strip()}" if relationship_type else ""
        if direction == "out":
            pattern = f"(n {{id:$id}})-[r{rel_spec}]->(neighbor)"
        elif direction == "in":
            pattern = f"(n {{id:$id}})<-[r{rel_spec}]-(neighbor)"
        else:
            pattern = f"(n {{id:$id}})-[r{rel_spec}]-(neighbor)"

        neighbor_query = f"""
            MATCH {pattern}
            RETURN neighbor.id, labels(neighbor), properties(neighbor),
                   type(r), properties(r), startNode(r).id, endNode(r).id
            LIMIT $limit
        """

        rows = graph.ro_query(neighbor_query, params={"id": norm_id, "limit": limit}).result_set

        neighbors_by_id: Dict[str, GraphNode] = {}
        edges_by_id: Dict[str, GraphEdge] = {}

        for row in rows:
            nbr_id, nbr_labels, nbr_props, r_type, r_props, s_id, t_id = row
            nid = str(nbr_id or "")
            if nid and nid not in neighbors_by_id:
                neighbors_by_id[nid] = GraphNode(
                    id=nid,
                    label=nbr_labels[0] if nbr_labels else "Node",
                    properties=sanitize_properties(dict(nbr_props or {})),
                )

            src = str(s_id or (norm_id if direction == "out" else nid))
            dst = str(t_id or (nid if direction == "out" else norm_id))
            eid = f"edge-{src}-{r_type}-{dst}"
            if eid not in edges_by_id:
                edges_by_id[eid] = GraphEdge(
                    id=eid,
                    source=src,
                    target=dst,
                    type=str(r_type or "CONNECTED_TO"),
                    properties=sanitize_properties(dict(r_props or {})),
                )

        return NeighborsResponse(
            node=central_node,
            neighbors=list(neighbors_by_id.values()),
            edges=list(edges_by_id.values()),
            meta=GraphMeta(
                node_count=len(neighbors_by_id) + 1,
                edge_count=len(edges_by_id),
                truncated=(len(rows) >= limit),
            ),
        )

    except Exception as exc:
        logger.error("Failed to query node neighbors for %s: %s", node_id, exc)
        return None
