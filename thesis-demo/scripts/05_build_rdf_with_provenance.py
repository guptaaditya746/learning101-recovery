#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS, XSD


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = PROJECT_ROOT / "data" / "graph_patch.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "graph" / "latest_graph.ttl"

KG = Namespace("https://example.org/thesis-demo/kg/")
PROV = Namespace("http://www.w3.org/ns/prov#")


RESERVED_NODE_KEYS = {
    "id",
    "type",
    "label",
    "name",
    "title",
    "provenance",
}

RESERVED_EDGE_KEYS = {
    "id",
    "type",
    "relation",
    "predicate",
    "source",
    "source_id",
    "from",
    "target",
    "target_id",
    "to",
    "provenance",
}


PROVENANCE_KEYS = [
    "paper_id",
    "paper",
    "doc_id",
    "document_id",
    "section",
    "section_title",
    "chunk_id",
    "chunk",
    "source_span",
    "span",
    "start_char",
    "end_char",
    "text_preview",
    "preview",
    "evidence",
    "source_text",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing graph patch: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def slugify(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "", text)
    text = text.strip("_")

    if not text:
        text = "unknown"

    return text[:180]


def safe_literal(value: Any) -> Literal:
    if isinstance(value, bool):
        return Literal(value, datatype=XSD.boolean)

    if isinstance(value, int):
        return Literal(value, datatype=XSD.integer)

    if isinstance(value, float):
        return Literal(value, datatype=XSD.decimal)

    return Literal(str(value))


def compact_text(text: str, max_chars: int = 500) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


def get_node_id(node: dict[str, Any], index: int) -> str:
    for key in ["id", "node_id", "uid"]:
        value = node.get(key)
        if value:
            return str(value)

    label = get_node_label(node)
    return f"node_{index}_{slugify(label)}"


def get_node_type(node: dict[str, Any]) -> str:
    return str(node.get("type") or node.get("node_type") or "Thing")


def get_node_label(node: dict[str, Any]) -> str:
    for key in ["label", "name", "title", "id"]:
        value = node.get(key)
        if value:
            return str(value)

    return "unknown"


def node_uri(node_id: str) -> URIRef:
    return KG[f"node/{slugify(node_id)}"]


def predicate_uri(edge_type: str) -> URIRef:
    return KG[slugify(edge_type.upper())]


def assertion_uri(source_id: str, edge_type: str, target_id: str, index: int) -> URIRef:
    raw = f"{source_id}|{edge_type}|{target_id}|{index}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return KG[f"assertion/{digest}"]


def get_edge_type(edge: dict[str, Any]) -> str:
    for key in ["type", "relation", "predicate", "edge_type"]:
        value = edge.get(key)
        if value:
            return str(value)

    return "RELATED_TO"


def get_edge_source(edge: dict[str, Any]) -> str | None:
    for key in ["source", "source_id", "from", "subject"]:
        value = edge.get(key)
        if value:
            return str(value)

    return None


def get_edge_target(edge: dict[str, Any]) -> str | None:
    for key in ["target", "target_id", "to", "object"]:
        value = edge.get(key)
        if value:
            return str(value)

    return None


def primitive(value: Any) -> bool:
    return isinstance(value, str | int | float | bool)


def extract_provenance(record: dict[str, Any]) -> dict[str, Any]:
    """
    Pull provenance from either:
    - top-level fields: paper_id, chunk_id, section, text_preview, ...
    - nested record["provenance"]
    """

    provenance: dict[str, Any] = {}

    nested = record.get("provenance")
    if isinstance(nested, dict):
        for key, value in nested.items():
            if value is not None and primitive(value):
                provenance[key] = value

    for key in PROVENANCE_KEYS:
        value = record.get(key)
        if value is not None and primitive(value):
            provenance[key] = value

    return provenance


def normalize_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize common aliases into stable KG fields.
    """

    normalized: dict[str, Any] = {}

    alias_map = {
        "paper": "paper_id",
        "doc_id": "paper_id",
        "document_id": "paper_id",
        "section_title": "section",
        "chunk": "chunk_id",
        "span": "source_span",
        "preview": "text_preview",
        "source_text": "text_preview",
        "evidence": "text_preview",
    }

    for key, value in provenance.items():
        clean_key = alias_map.get(key, key)

        if clean_key == "text_preview":
            value = compact_text(str(value))

        normalized[clean_key] = value

    return normalized


def add_provenance_triples(
    graph: Graph,
    subject: URIRef,
    provenance: dict[str, Any],
) -> None:
    provenance = normalize_provenance(provenance)

    for key, value in provenance.items():
        if value is None:
            continue

        graph.add((subject, KG[slugify(key)], safe_literal(value)))

    if provenance:
        graph.add((subject, PROV.wasDerivedFrom, Literal("graph_patch.json")))


def add_node_triples(
    graph: Graph,
    node: dict[str, Any],
    node_id: str,
) -> None:
    uri = node_uri(node_id)
    node_type = get_node_type(node)
    label = get_node_label(node)

    graph.add((uri, RDF.type, KG.Node))
    graph.add((uri, RDF.type, KG[slugify(node_type)]))
    graph.add((uri, KG.nodeType, Literal(node_type)))
    graph.add((uri, RDFS.label, Literal(label)))

    provenance = extract_provenance(node)
    add_provenance_triples(graph, uri, provenance)

    for key, value in node.items():
        if key in RESERVED_NODE_KEYS:
            continue

        if key in PROVENANCE_KEYS:
            continue

        if primitive(value):
            graph.add((uri, KG[slugify(key)], safe_literal(value)))


def add_edge_triples(
    graph: Graph,
    edge: dict[str, Any],
    edge_index: int,
    nodes_by_id: dict[str, dict[str, Any]],
) -> bool:
    source_id = get_edge_source(edge)
    target_id = get_edge_target(edge)
    edge_type = get_edge_type(edge)

    if not source_id or not target_id:
        return False

    s = node_uri(source_id)
    p = predicate_uri(edge_type)
    o = node_uri(target_id)

    # Keep the simple graph fact easy to query.
    graph.add((s, p, o))

    # Add an assertion node so provenance can attach to this specific edge.
    assertion = assertion_uri(source_id, edge_type, target_id, edge_index)

    graph.add((assertion, RDF.type, KG.EdgeAssertion))
    graph.add((assertion, RDF.subject, s))
    graph.add((assertion, RDF.predicate, p))
    graph.add((assertion, RDF.object, o))

    graph.add((assertion, KG.edgeType, Literal(edge_type)))
    graph.add((assertion, KG.sourceNode, s))
    graph.add((assertion, KG.targetNode, o))

    # Edge provenance first, then target/source fallback.
    provenance = extract_provenance(edge)

    if not provenance and target_id in nodes_by_id:
        provenance = extract_provenance(nodes_by_id[target_id])

    if not provenance and source_id in nodes_by_id:
        provenance = extract_provenance(nodes_by_id[source_id])

    add_provenance_triples(graph, assertion, provenance)

    for key, value in edge.items():
        if key in RESERVED_EDGE_KEYS:
            continue

        if key in PROVENANCE_KEYS:
            continue

        if primitive(value):
            graph.add((assertion, KG[slugify(key)], safe_literal(value)))

    return True


def build_graph(patch: dict[str, Any]) -> tuple[Graph, dict[str, int]]:
    graph = Graph()

    graph.bind("kg", KG)
    graph.bind("prov", PROV)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("dcterms", DCTERMS)

    graph.add((KG.Dataset, RDF.type, KG.GraphDataset))
    graph.add((KG.Dataset, DCTERMS.title, Literal("Thesis demo scientific-paper KG")))

    nodes = patch.get("nodes", [])
    edges = patch.get("edges", [])

    if not isinstance(nodes, list):
        raise ValueError("Expected graph_patch.json to contain a list at key: nodes")

    if not isinstance(edges, list):
        raise ValueError("Expected graph_patch.json to contain a list at key: edges")

    nodes_by_id: dict[str, dict[str, Any]] = {}

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue

        node_id = get_node_id(node, index)
        nodes_by_id[node_id] = node
        add_node_triples(graph, node, node_id)

    added_edges = 0

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue

        ok = add_edge_triples(
            graph=graph,
            edge=edge,
            edge_index=index,
            nodes_by_id=nodes_by_id,
        )

        if ok:
            added_edges += 1

    stats = {
        "nodes": len(nodes_by_id),
        "edges": added_edges,
        "triples": len(graph),
    }

    return graph, stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build RDF/Turtle KG with explicit provenance assertion nodes."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    args = parser.parse_args()

    patch = load_json(args.input)
    graph, stats = build_graph(patch)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=args.output, format="turtle")

    print(f"Wrote: {args.output}")
    print(f"Nodes: {stats['nodes']}")
    print(f"Edges: {stats['edges']}")
    print(f"Triples: {stats['triples']}")


if __name__ == "__main__":
    main()
