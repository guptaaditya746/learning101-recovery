from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from rdflib import Graph


def local_name(uri: object) -> str:
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe EdgeAssertion nodes in the RDF graph."
    )
    parser.add_argument(
        "--graph",
        default="graph/latest_graph.ttl",
        help="Path to Turtle RDF graph.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of EdgeAssertion nodes to show.",
    )
    args = parser.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    g = Graph()
    g.parse(graph_path, format="turtle")

    edge_query = """
    SELECT ?edge ?type
    WHERE {
      ?edge a ?type .
      FILTER(STRENDS(STR(?type), "EdgeAssertion"))
    }
    LIMIT 100
    """

    edges = list(g.query(edge_query))

    print(f"Loaded graph: {graph_path}")
    print(f"Triples: {len(g)}")
    print(f"EdgeAssertion nodes found: {len(edges)}")

    if not edges:
        print("\nNo EdgeAssertion nodes found. Check the RDF class name.")
        return

    predicate_counts: dict[str, int] = defaultdict(int)
    sample_edges = edges[: args.limit]

    print("\n=== Sample EdgeAssertion nodes ===")

    for row in sample_edges:
        edge = row.edge
        print(f"\nEDGE: {edge}")

        for p, o in g.predicate_objects(edge):
            pname = local_name(p)
            predicate_counts[pname] += 1
            print(f"  {pname}: {o}")

    print("\n=== Predicate names seen in samples ===")
    for name, count in sorted(predicate_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"{name}: {count}")

    print("\n=== Candidate provenance/chunk predicates ===")
    candidate_query = """
    SELECT DISTINCT ?p ?o
    WHERE {
      ?edge a ?type .
      FILTER(STRENDS(STR(?type), "EdgeAssertion"))
      ?edge ?p ?o .
      FILTER(
        CONTAINS(LCASE(STR(?p)), "chunk") ||
        CONTAINS(LCASE(STR(?p)), "source") ||
        CONTAINS(LCASE(STR(?p)), "provenance") ||
        CONTAINS(LCASE(STR(?p)), "evidence") ||
        CONTAINS(LCASE(STR(?o)), "_chunk_")
      )
    }
    LIMIT 50
    """

    for row in g.query(candidate_query):
        print(f"{local_name(row.p)}: {row.o}")


if __name__ == "__main__":
    main()
